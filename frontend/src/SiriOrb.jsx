import { useState, useRef, useEffect } from 'react'
import './SiriOrb.css'

const API_URL = 'http://localhost:8000/api/siri-chat'

const STATE_META = {
  idle:      { label: 'Tap to speak', icon: '🎙️' },
  listening: { label: 'Listening…',   icon: '👂'  },
  thinking:  { label: 'Thinking…',    icon: '✦'   },
  speaking:  { label: 'Tap to stop',  icon: '🔊'  },
  error:     { label: 'Try again',    icon: '⚠️'   },
}

// BCP-47 tags for speechSynthesis
const LANG_TAG = {
  'en-IN': 'en-IN', 'hi-IN': 'hi-IN', 'mr-IN': 'mr-IN',
  'bn-IN': 'bn-IN', 'ta-IN': 'ta-IN', 'te-IN': 'te-IN',
  'gu-IN': 'gu-IN', 'kn-IN': 'kn-IN',
}

export default function SiriOrb({ onResult }) {
  const [status,   setStatus]   = useState('idle')
  const [isPaused, setIsPaused] = useState(false)
  const [errMsg,   setErrMsg]   = useState('')

  const mediaRecorderRef = useRef(null)
  const chunksRef        = useRef([])
  // AudioContext — created once on first user gesture, stays alive
  const audioCtxRef      = useRef(null)
  // Which audio path is currently playing: 'synthesis' | 'sarvam' | null
  const activePathRef    = useRef(null)
  // Refs to the active playback objects so we can pause/stop them
  const sourceNodeRef    = useRef(null)   // AudioContext BufferSource (Sarvam path)
  const keepAliveRef     = useRef(null)   // Chrome synthesis keep-alive timer

  useEffect(() => {
    // Pre-populate the voice list so it's ready when we need it
    window.speechSynthesis?.getVoices()
    const sync = () => window.speechSynthesis?.getVoices()
    window.speechSynthesis?.addEventListener('voiceschanged', sync)
    return () => {
      stopAll()
      window.speechSynthesis?.removeEventListener('voiceschanged', sync)
      stopMicStream()
    }
  }, [])

  // ── AudioContext helpers ────────────────────────────────────────────
  function getAudioCtx() {
    if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
      audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)()
    }
    return audioCtxRef.current
  }

  // Call this synchronously in every click handler to keep audio unlocked
  function unlockAudio() {
    try {
      const ctx = getAudioCtx()
      if (ctx.state === 'suspended') ctx.resume()
    } catch (_) {}
  }

  // ── Stop everything ─────────────────────────────────────────────────
  function stopAll() {
    // Stop AudioContext playback
    try { sourceNodeRef.current?.stop() } catch (_) {}
    sourceNodeRef.current = null

    // Stop browser synthesis
    window.speechSynthesis?.cancel()
    clearInterval(keepAliveRef.current)

    activePathRef.current = null
  }

  // ── Path A: Web Speech API (guaranteed to narrate in all languages) ──
  // Starts immediately as the primary/fallback narration. If Sarvam audio
  // decodes successfully (Path B), it cancels synthesis and takes over.
  function doSynthesis(text, lang) {
    window.speechSynthesis.cancel()
    clearInterval(keepAliveRef.current)

    const utt    = new SpeechSynthesisUtterance(text)
    utt.lang     = LANG_TAG[lang] ?? 'en-IN'
    utt.rate     = 0.88
    utt.pitch    = 1.05
    utt.volume   = 1

    const voices = window.speechSynthesis.getVoices()
    const match  = voices.find(v => v.lang === utt.lang)
                ?? voices.find(v => v.lang.startsWith(utt.lang.split('-')[0]))
    if (match) utt.voice = match

    function onDone() {
      clearInterval(keepAliveRef.current)
      activePathRef.current = null
      setStatus('idle')
      setIsPaused(false)
    }
    utt.onend  = onDone
    utt.onerror = onDone

    // Chrome stops mid-utterance after ~15 s — nudge it periodically
    keepAliveRef.current = setInterval(() => {
      if (!window.speechSynthesis.speaking) { clearInterval(keepAliveRef.current); return }
      if (!window.speechSynthesis.paused) {
        window.speechSynthesis.pause()
        window.speechSynthesis.resume()
      }
    }, 10_000)

    activePathRef.current = 'synthesis'
    window.speechSynthesis.speak(utt)
  }

  // ── Path B: Sarvam audio via AudioContext ───────────────────────────
  // Runs in parallel with Path A. If decode succeeds, synthesis is
  // cancelled and higher-quality Sarvam audio plays instead.
  function trySarvamAudio(b64) {
    const ctx = getAudioCtx()
    try {
      const binary = atob(b64)
      const bytes  = new Uint8Array(binary.length)
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)

      ctx.decodeAudioData(bytes.buffer.slice(0))
        .then(audioBuffer => {
          // Sarvam decoded OK — take over from synthesis
          window.speechSynthesis.cancel()
          clearInterval(keepAliveRef.current)
          sourceNodeRef.current?.stop()

          const src = ctx.createBufferSource()
          src.buffer  = audioBuffer
          src.connect(ctx.destination)
          src.onended = () => {
            sourceNodeRef.current  = null
            activePathRef.current  = null
            setStatus('idle')
            setIsPaused(false)
          }
          sourceNodeRef.current = src
          activePathRef.current = 'sarvam'

          // Respect paused state if user paused during the decode delay
          if (isPaused) {
            src.start(0)
            ctx.suspend()
          } else {
            src.start(0)
          }
        })
        .catch(err => {
          // Decode failed — synthesis is already narrating, so just log
          console.warn('Sarvam audio decode failed (synthesis is active):', err)
        })
    } catch (err) {
      console.warn('Sarvam audio playback error (synthesis is active):', err)
    }
  }

  // ── Main narration entry point ──────────────────────────────────────
  function speakResponse(text, lang, audioB64) {
    if (!text) { setStatus('idle'); return }
    setStatus('speaking')
    setIsPaused(false)

    // Always start synthesis first — zero latency, guaranteed to work
    doSynthesis(text, lang)

    // Concurrently attempt to upgrade to Sarvam audio
    if (audioB64) trySarvamAudio(audioB64)
  }

  // ── Pause / Resume ──────────────────────────────────────────────────
  function togglePause() {
    if (status !== 'speaking') return

    if (isPaused) {
      if (activePathRef.current === 'synthesis') {
        window.speechSynthesis.resume()
      } else if (activePathRef.current === 'sarvam') {
        audioCtxRef.current?.resume()
      }
      setIsPaused(false)
    } else {
      if (activePathRef.current === 'synthesis') {
        window.speechSynthesis.pause()
      } else if (activePathRef.current === 'sarvam') {
        audioCtxRef.current?.suspend()
      }
      setIsPaused(true)
    }
  }

  // ── Microphone helpers ──────────────────────────────────────────────
  function stopMicStream() {
    const mr = mediaRecorderRef.current
    if (mr?.stream) mr.stream.getTracks().forEach(t => t.stop())
  }

  // ── Main click handler ──────────────────────────────────────────────
  async function handleClick() {
    unlockAudio()   // sync — must precede any await

    if (status === 'speaking') {
      stopAll()
      setStatus('idle')
      return
    }
    if (status === 'thinking') return

    if (status === 'listening') {
      mediaRecorderRef.current?.stop()
      return
    }

    // ── Start recording ─────────────────────────────────────────────
    setErrMsg('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr     = new MediaRecorder(stream)
      mediaRecorderRef.current = mr
      chunksRef.current        = []

      mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }

      mr.onstop = async () => {
        stopMicStream()
        setStatus('thinking')

        const mimeType = mr.mimeType || 'audio/webm'
        const ext      = mimeType.includes('ogg') ? 'ogg' : 'webm'
        const blob     = new Blob(chunksRef.current, { type: mimeType })
        const formData = new FormData()
        formData.append('audio', blob, `audio.${ext}`)

        try {
          const res  = await fetch(API_URL, { method: 'POST', body: formData })
          const data = await res.json()

          if (!res.ok || !data.success) {
            throw new Error(data.detail || data.error || 'API error')
          }

          onResult({
            transcription: data.transcription,
            response:      data.response,
            language:      data.language,
            topicData:     data.topic_data ?? null,
          })

          // Narrate the response (synthesis + optional Sarvam upgrade)
          speakResponse(data.response, data.language, data.audio_base64)
        } catch (err) {
          console.error('siri-chat error:', err)
          setErrMsg(err.message)
          setStatus('error')
          setTimeout(() => setStatus('idle'), 3000)
        }
      }

      mr.start()
      setStatus('listening')
    } catch (err) {
      console.error('Mic error:', err)
      setErrMsg('Microphone access denied.')
      setStatus('error')
      setTimeout(() => setStatus('idle'), 3000)
    }
  }

  const meta = STATE_META[status] ?? STATE_META.idle

  return (
    <div className="orb-wrapper">
      {status === 'listening' && (
        <>
          <div className="ring ring-1" />
          <div className="ring ring-2" />
          <div className="ring ring-3" />
        </>
      )}

      <button
        className={`orb orb--${status}`}
        onClick={handleClick}
        aria-label={meta.label}
        aria-pressed={status === 'listening'}
      >
        <span className="orb-icon">{meta.icon}</span>
      </button>

      <p className={`orb-label orb-label--${status}`}>{errMsg || meta.label}</p>

      {/* Pause / Resume — visible only while speaking */}
      {status === 'speaking' && (
        <button
          className={`pause-btn ${isPaused ? 'pause-btn--paused' : ''}`}
          onClick={togglePause}
          aria-label={isPaused ? 'Resume narration' : 'Pause narration'}
        >
          <span className="pause-icon" aria-hidden="true">
            {isPaused ? '▶' : '⏸'}
          </span>
          <span className="pause-text">{isPaused ? 'Resume' : 'Pause'}</span>
        </button>
      )}
    </div>
  )
}
