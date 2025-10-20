# app/root_cause_analyzer.py
def find_root_cause(detected_bugs):
    # detected_bugs: list of strings where each begins with "[ERROR] service ..."
    counts = {}
    for b in detected_bugs:
        if b.startswith("[ERROR] "):
            try:
                rest = b[len("[ERROR] "):]
                svc = rest.split()[0]
                counts[svc] = counts.get(svc,0) + 1
            except:
                pass
    if not counts:
        return {"result":"no_root_found"}
    top = max(counts, key=lambda k:counts[k])
    return {"root_service": top, "count": counts[top]}
