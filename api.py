# ================= MIX (TOP 5 MOST VIEWED – FIXED & FAST) =================
@app.get("/mix")
def mix():
    try:
        cmd = [
            YTDLP,
            "--quiet",
            "--no-warnings",
            "--skip-download",
            "--socket-timeout", "10",
            "--dump-json",
            "ytsearch10:music"
        ]

        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30   # 🔥 increased
        )

        results = []

        for line in p.stdout.strip().split("\n"):
            try:
                data = json.loads(line)
            except:
                continue

            views = data.get("view_count")
            if not views:
                continue

            results.append({
                "title": data.get("title"),
                "url": f"https://youtu.be/{data.get('id')}",
                "thumbnail": data.get("thumbnail"),
                "duration": format_duration(data.get("duration")),
                "duration_sec": data.get("duration"),
                "views": views
            })

        if not results:
            return JSONResponse({"error": "no_mix_results"}, status_code=404)

        top5 = sorted(results, key=lambda x: x["views"], reverse=True)[:5]

        return {
            "type": "mix",
            "count": len(top5),
            "results": top5
        }

    except subprocess.TimeoutExpired:
        return JSONResponse({"error": "mix_timeout"}, status_code=504)
    except Exception as e:
        return JSONResponse({"error": "mix_failed", "detail": str(e)}, status_code=500)
