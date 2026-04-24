import os


def main() -> None:
    process_type = os.getenv("PROCESS_TYPE", "api").strip().lower()

    if process_type == "worker":
        os.environ["ENABLE_SCHEDULER"] = "true"
        from app.worker import main as worker_main

        worker_main()
        return

    os.environ["ENABLE_SCHEDULER"] = "false"
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WEB_CONCURRENCY", "2"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, workers=workers)


if __name__ == "__main__":
    main()
