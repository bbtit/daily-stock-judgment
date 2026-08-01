module.exports = {
  ci: {
    collect: {
      url: ["http://127.0.0.1:8000/"],
      startServerCommand:
        "DSJ_MARKET=demo DSJ_JUDGMENT_MODEL=demo DSJ_AS_OF=2026-07-31 DSJ_DB_PATH=data/lhci.db uv run daily-stock-judgment",
      startServerReadyPattern: "Uvicorn running",
      numberOfRuns: 1,
    },
    upload: {
      target: "filesystem",
      outputDir: ".lighthouseci-reports",
    },
  },
};
