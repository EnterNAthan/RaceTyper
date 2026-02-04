import uvicorn

if __name__ == "__main__":
    uvicorn.run("server_app.app:app", host="0.0.0.0", reload=True, port=8080)
