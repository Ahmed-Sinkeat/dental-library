#!/usr/bin/env python3
"""Classify every media file of the channel into library/<Subject>/<Topic>/ from the signals in result.json
(file name, audio title, captions, subject-header posts, trailing captions, first slide text).
Usage: python3 catalog.py           # writes catalog.csv + prints stats + selftest
       python3 catalog.py --apply   # server-side copy channel/ -> library/ inside R2, then verify
"""
import csv, json, re, subprocess, sys, zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).parent
SRC, OUT = ROOT / "channel", ROOT / "channel_r2"
RENAMES = json.loads((ROOT / "channel_r2.renames.json").read_text())
BUCKET = "r2:ahmedbadr-channel"

ANAT, NEURO, PHYS, BIO = "Head and Neck Anatomy", "Neuroanatomy", "Physiology", "Oral Biology and Histology"
GPATH, OPATH, OMED = "General Pathology", "Oral Pathology", "Oral Medicine and Diagnosis"
OMFS, PERIO, ORTHO = "Oral and Maxillofacial Surgery", "Periodontics", "Orthodontics"
PEDO, OPER, MAT = "Paediatric Dentistry", "Operative Dentistry and Endodontics", "Dental Materials"
RAD, MED, SURG = "Oral Radiology", "Medicine and Medically Compromised Patients", "General Surgery"
PHARM, PROS, POSTS, GEN = "Pharmacology and Prescriptions", "Prosthodontics", "Channel Posts", "General Dentistry"

# (regex on normalised text, subject, topic) - first hit wins, most specific first.
RULES = [(re.compile(p), s, t) for p, s, t in [
    (r"pdf \d+prosthodontics", PROS, "History Sheets"), (r"pdf \d+pedo", PEDO, "History Sheets"),
    (r"pdf \d+perio", PERIO, "History Sheets"), (r"pdf \d+surger", OMFS, "History and Examination"),
    (r"pdf \d+cons", OPER, "History Sheets"),
    (r"history sheet review|history (and|&) examination|هستوري|هسيتوري", OMFS, "History and Examination"),
    (r"history sheets", OMED, "History Sheets"),
    (r"crinal|cranial nerve exam", OMFS, "History and Examination"),
    (r"neck lump|neck mass|lymph", OMFS, "Neck Swellings"),
    (r"salivary|savilary|salivry|\bs g ?2\b", OMFS, "Salivary Glands"),
    (r"neuro|spinal cord|\bspc\b|brain stem|\bcsf\b|summery cn|cranial nerve summ", NEURO, "Neuroanatomy Course"),
    (r"head (and|&) neck|collection|anatomy", ANAT, "Notes and Revision"),
    (r"revision|spotting|omfs exam|permanent exam|aud 20240428", OMFS, "Exam Revision"),
    (r"trigeminal neuralgia", OMFS, "Trigeminal Neuralgia"), (r"facial palsy|facial nerve", OMFS, "Facial Palsy"),
    (r"\btmj\b|temporomandibular", OMFS, "TMJ Diseases"),
    (r"osteomyelitis|fibro|bone pathology|bone lesions|orofacial bone|developmental jaws|giant cell|gaint", OPATH, "Bone and Jaw Lesions"),
    (r"odontogenic|cyst|radiolucen", OPATH, "Cysts and Tumours"),
    (r"dry socke?t|dry soc", OMFS, "Dry Socket"),
    (r"caries|\bdc\b|\bdc ?\d|consequence|sequelae|periradicular", OPATH, "Dental Caries and Sequelae"),
    (r"anomal|malformation|abnormalities of teeth", OPATH, "Developmental Anomalies"),
    (r"oral pathology videos", OPATH, "Videos"),
    (r"oral cancer|\bcancer\b|oncolog", OMED, "Oral Cancer"), (r"oral ulcer", OMED, "Oral Ulcers"),
    (r"prescription|analgesic|antibiotic|مضاد", PHARM, "Prescriptions"),
    (r"anesth|anethesia|techniques of la|\bla complications|nerve block|palatine|trigeminal nerve", OMFS, "Local Anaesthesia"),
    (r"bleeding in dentist|post extraction bleeding", OMFS, "Bleeding Management"),
    (r"exodontia|extraction|impaction|exdontia|الخلع|القلع|\bslob\b", OMFS, "Exodontia"),
    (r"trauma|truma|fracture", OMFS, "Trauma"), (r"emergenc", OMFS, "Medical Emergencies"),
    (r"implant", OMFS, "Implantology"), (r"omfs contents", OMFS, "Overview"),
    (r"periapical|endodontic", OPER, "Endodontics"),
    (r"operative|cavity preparation|class \d|conservation", OPER, "Operative Dentistry"),
    (r"hsv|herpes|acute gingival", PERIO, "Acute Gingival Infections"),
    (r"chronic periodontitis|aggressive periodontitis", PERIO, "Periodontitis"),
    (r"etiology of periodontal", PERIO, "Etiology"), (r"gingival enlarg", PERIO, "Gingival Enlargement"),
    (r"perio|gingiv|preparation of mouth", PERIO, "General"),
    (r"pulp therapy|paedodontic", PEDO, "Pulp Therapy"),
    (r"amalgam|composite|ceramic|dental material", MAT, "Materials"),
    (r"orthodont|malocclusion|dentitions period", ORTHO, "General"),
    (r"autonomic|endocrin|parathyroid|pos pitut|\bptg\b|homeostasis|physiology", PHYS, "General"),
    (r"enamel|dentin|cementum|سمنتم|alveolar bone|development and growth|primary teeth|^primary\b|premolar|canin|dental morphology|oral biology", BIO, "Oral Histology and Morphology"),
    (r"radiograph|radiolog|^presentation ?1\b", RAD, "Radiographs"),
    (r"obstructive|surgical site|g surgery", SURG, "General Surgery"),
    (r"blood pressure", MED, "Clinical Skills"),
    (r"\bdm ?\d|diabet", MED, "Diabetes"), (r"cvs|stroke|\bcva\b|myocardial|\bmi\b|hypertension|\bhnt", MED, "Cardiovascular and Stroke"),
    (r"anemia|^a ?\d|hemoph|bleeding disorders|\bbd ?\d|heam|hematolog", MED, "Hematology"),
    (r"renal|ckd", MED, "Renal"), (r"thyr|\btg ?\d|\bt g\b", MED, "Endocrine and Thyroid"),
    (r"hepat|\bibd|inflammatory|diarrh|malabsor|\bju ?\d", MED, "GIT and Liver"), (r"\bhiv\b", MED, "HIV"),
    (r"corticosteroid", MED, "Corticosteroids"), (r"pregnan", MED, "Pregnancy"),
    (r"medical compromise|medically ?compromised|mcps?\b|scully", MED, "Medically Compromised Patients"),
    (r"general medicine", MED, "General Medicine"),
    (r"oral surgery", OMFS, "General"), (r"oral pathology", OPATH, "General"),
]]
BOOKS = [(re.compile(p), s) for p, s in [
    (r"snell|gray|colour atlas|langman", ANAT), (r"lippincott", PHARM), (r"brs physiology", PHYS),
    (r"orthodontic", ORTHO), (r"mcqs in oral|neville|oral and maxillofacial pathology", OPATH),
    (r"preclinical|conservative", OPER), (r"ten cate", BIO), (r"pathoma|general pathology|systemic pathology", GPATH),
    (r"oral diagnosis|oral medicine|diferential|oral cancer|precancer|oncology|handbook of oral", OMED),
    (r"contemporary oral and maxillofacial|peterson|local anesthesia", OMFS), (r"scully|medical problems", MED),
    (r"dental pulse", GEN)]]
# checked by eye (contact sheet / first slide): basename prefix -> (subject, topic); topic None = reference book
OVERRIDE = {"video_2@": (OMFS, "Local Anaesthesia"), "video_3@": (OMFS, "Local Anaesthesia"),
            "photo_4@": (OMFS, "Local Anaesthesia"), "photo_6@": (OMED, "Oral Cancer"),
            "photo_15@": (NEURO, "Neuroanatomy Course"), "Presentation 2.pptx": (OMFS, "Local Anaesthesia"),
            "chapter 1.pdf": (OPATH, None), "Share with CamScanner.zip": (OPATH, None)}
BOOK_HINT = re.compile(r"modernlibrary|dentistry_lecture|مرجع")


def norm(s):
    return re.sub(r"[_.\-\s]+", " ", s.lower()).strip()


def classify(text):
    t = norm(text)
    for rx, s, topic in RULES:
        if rx.search(t):
            return s, topic
    return None


def meta(m):  # audio tags: title + performer, minus the channel name and "<unknown>"
    return " ".join(str(m.get(k, "")) for k in ("title", "performer") if "unknown" not in str(m.get(k, "")) and "alkhazin" not in str(m.get(k, "")))


def txt(m):
    t = m.get("text", "")
    return t if isinstance(t, str) else "".join(e if isinstance(e, str) else e.get("text", "") for e in t)


def slide_text(p):
    try:
        with zipfile.ZipFile(p) as z:
            return " ".join(re.sub(r"<[^>]+>", " ", z.read(f"ppt/slides/slide{i}.xml").decode("utf8", "ignore"))
                            for i in (1, 2) if f"ppt/slides/slide{i}.xml" in z.namelist())
    except Exception:
        return ""


def build():
    msgs = json.loads((SRC / "result.json").read_text(encoding="utf-8"))["messages"]
    votes, name_text, first_date, caps = defaultdict(Counter), defaultdict(str), {}, defaultdict(str)
    header = None
    for i, m in enumerate(msgs):
        f, t = m.get("file") or m.get("photo"), txt(m).strip()
        if not f:
            if t and len(t) < 90 and not t.startswith("http") and classify(t):
                header = (m["date"][:10], classify(t))
            continue
        first_date.setdefault(f, m["date"][:10])
        name_text[f] = f"{Path(f).name} {meta(m)}"
        caps[f] += " " + t
        lead = header[1] if header and header[0] == m["date"][:10] else None
        nxt = msgs[i + 1] if i + 1 < len(msgs) else {}
        trail = (classify(txt(nxt)) if nxt and not (nxt.get("file") or nxt.get("photo"))
                 and nxt["date"][:10] == m["date"][:10] and not lead and len(txt(nxt)) < 90
                 and not txt(nxt).lstrip().startswith(("#", "@")) else None)
        if lead or trail:
            votes[f][lead or trail] += 1
    rows = []
    for f in sorted(first_date, key=first_date.get):
        base = Path(f).name
        new = RENAMES.get(f, f)
        r = dict(old=f, channel_path=new, date=first_date[f], clue="", confidence="")
        cap = caps[f]
        ov = next((v for k, v in OVERRIDE.items() if base.startswith(k)), None)
        if ov:
            d = f"library/Reference Books/{ov[0]}" if ov[1] is None else f"library/{ov[0]}/{ov[1]}"
            r.update(subject=ov[0], topic=ov[1] or "", dest=f"{d}/{Path(new).name}", clue="checked by eye", confidence="sure")
            rows.append(r)
            continue
        bookish = f.lower().endswith(("pdf", "zip")) or "." not in base
        book = next((s for rx, s in BOOKS if rx.search(norm(base))), None) if bookish else None
        if book or (bookish and BOOK_HINT.search(cap.lower())):
            hit = (book, "") if book else classify(cap) or (GEN, "")
            r.update(subject=hit[0], topic="", dest=f"library/Reference Books/{hit[0]}/{Path(new).name}",
                     clue="book", confidence="sure" if book else "likely")
        else:
            hit = classify(name_text[f])
            if hit and not base.startswith(("photo_", "record", "video_")):
                r.update(clue="file name", confidence="sure")
            elif base.startswith("photo_"):
                hit = classify(cap) if len(cap.strip()) < 60 else None
                r.update(clue="caption" if hit else "poster", confidence="sure" if hit else "likely")
                hit = hit or (POSTS, "Posters")
            elif not hit or base.startswith(("record", "video_")):
                hit = classify(name_text[f] + " " + cap)
                if hit:
                    r.update(clue="title/caption", confidence="sure")
            if not hit and votes[f]:
                hit = votes[f].most_common(1)[0][0]
                r.update(clue="subject header", confidence="likely")
            if not hit and base.lower().endswith((".pptx", ".pptm")):
                hit = classify(slide_text(SRC / f))
                if hit:
                    r.update(clue="slide text", confidence="likely")
            if not hit:
                hit, r["clue"], r["confidence"] = ("Unsorted", ""), "none", "guess"
            r.update(subject=hit[0], topic=hit[1])
            r["dest"] = f"library/{hit[0]}/{hit[1]}/{Path(new).name}".replace("//", "/")
        rows.append(r)
    # pair record(N).mp4 with the audio posted right next to it (title of the .ogg names the topic)
    byold = {r["old"]: r for r in rows}
    for i, m in enumerate(msgs):
        f = m.get("file")
        if f and Path(f).suffix.lower() == ".mp4" and byold[f]["confidence"] == "guess" or (f and f in byold and byold[f]["clue"] == "none"):
            for n in msgs[i + 1:i + 4]:
                g = n.get("file")
                if g and meta(n) and classify(meta(n)):
                    s, t = classify(meta(n))
                    byold[f].update(subject=s, topic=t, clue="paired audio title", confidence="likely",
                                    dest=f"library/{s}/{t}/{Path(byold[f]['channel_path']).name}")
                    break
    seen = {}
    for r in rows:  # same destination for two different files -> add the date
        if r["dest"] in seen:
            p = Path(r["dest"]); r["dest"] = str(p.with_name(f"{p.stem} ({r['date']}){p.suffix}"))
        seen[r["dest"]] = r["old"]
    return rows


def selftest(rows):
    assert len({r["dest"] for r in rows}) == len(rows), "destination collision"
    for r in rows:
        assert (OUT / r["channel_path"]).is_file(), f"missing source {r['channel_path']}"
    print("selftest OK:", len(rows), "files, all sources exist, all destinations unique")


def copy(r):
    p = subprocess.run(["rclone", "copyto", f"{BUCKET}/channel/{r['channel_path']}", f"{BUCKET}/{r['dest']}"],
                       capture_output=True, text=True)
    return r, p.returncode, p.stderr[-200:]


if __name__ == "__main__":
    rows = build()
    cols = ["old", "channel_path", "dest", "subject", "topic", "confidence", "clue", "date"]
    with open(ROOT / "catalog.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    selftest(rows)
    print(Counter(r["confidence"] for r in rows))
    for s, n in Counter(r["subject"] for r in rows).most_common():
        print(f"{n:4d}  {s}")
    if "--apply" in sys.argv:
        with ThreadPoolExecutor(8) as ex:
            bad = [x for x in ex.map(copy, rows) if x[1]]
        print("copy failures:", len(bad), [(b[0]["dest"], b[2]) for b in bad[:3]])
        (ROOT / "catalog.csv").exists() and subprocess.run(
            ["rclone", "copyto", str(ROOT / "catalog.csv"), f"{BUCKET}/library/_catalog.csv"])
