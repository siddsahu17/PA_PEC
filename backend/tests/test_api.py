def test_health_check(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "Conversational Learning Assistant"}

def test_image_analyze_invalid_type(client):
    # Missing file upload simulation by making a normal POST without multipart data
    response = client.post("/image/analyze")
    assert response.status_code == 422 # Unprocessable Entity - missing file
