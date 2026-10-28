#!/usr/bin/env python3
"""catalog.csv + channel/result.json -> src/data/library.mjs (subjects, lessons with real attachments).
A lesson = one topic folder (teaching/exam) or one book (reference). Re-run after changing catalog.csv."""
import csv, json, os, re
from pathlib import Path

ROOT = Path(__file__).parent
# subject folder -> (id, icon, tone [css colour class], English, Arabic)
SUBJECTS = {
    "Head and Neck Anatomy": ("head-neck-anatomy", "anatomy", "anatomy", "Head & neck anatomy", "تشريح الرأس والعنق"),
    "Neuroanatomy": ("neuroanatomy", "anatomy", "anatomy", "Neuroanatomy", "التشريح العصبي"),
    "Physiology": ("physiology", "medical", "medicine", "Physiology", "الفسيولوجيا"),
    "Oral Biology and Histology": ("oral-biology", "cells", "pathology", "Oral biology & histology", "بيولوجيا الفم وعلم الأنسجة"),
    "General Pathology": ("general-pathology", "cells", "pathology", "General pathology", "الباثولوجيا العامة"),
    "Oral Pathology": ("oral-pathology", "cells", "pathology", "Oral pathology", "أمراض الفم (الباثولوجيا)"),
    "Oral Medicine and Diagnosis": ("oral-medicine", "medical", "medicine", "Oral medicine & diagnosis", "طب الفم والتشخيص"),
    "Oral and Maxillofacial Surgery": ("surgery", "tooth", "surgery", "Oral & maxillofacial surgery", "جراحة الفم والوجه والفكين"),
    "Periodontics": ("periodontics", "tooth", "surgery", "Periodontics", "أمراض اللثة"),
    "Orthodontics": ("orthodontics", "spark", "pediatric", "Orthodontics", "تقويم الأسنان"),
    "Paediatric Dentistry": ("pediatric", "spark", "pediatric", "Pediatric dentistry", "طب أسنان الأطفال"),
    "Operative Dentistry and Endodontics": ("operative", "layers", "materials", "Operative & endodontics", "الأسنان الترميمية وعلاج الجذور"),
    "Dental Materials": ("materials", "layers", "materials", "Dental materials", "المواد السنية"),
    "Oral Radiology": ("radiology", "medical", "medicine", "Oral radiology", "الأشعة السنية"),
    "Medicine and Medically Compromised Patients": ("medicine", "medical", "medicine", "Medicine & compromised patients", "الطب الباطني والمرضى ذوو الحالات الخاصة"),
    "General Surgery": ("general-surgery", "tooth", "surgery", "General surgery", "الجراحة العامة"),
    "Pharmacology and Prescriptions": ("pharmacology", "medical", "medicine", "Pharmacology & prescriptions", "الأدوية والوصفات الطبية"),
    "Prosthodontics": ("prosthodontics", "layers", "materials", "Prosthodontics", "التعويضات السنية"),
    "General Dentistry": ("general-dentistry", "book", "anatomy", "General dentistry", "طب الأسنان العام"),
}
SKIP_SUBJECTS = {"Channel Posts"}  # posters/ads stay in R2 but are not lessons
# "Subject|Topic" -> (English title, Arabic title)
TOPICS = {
    "Dental Materials|Materials": ("Amalgam, composite & ceramics", "الأملغم والكومبوزيت والسيراميك"),
    "General Surgery|General Surgery": ("General surgery notes", "ملاحظات الجراحة العامة"),
    "Head and Neck Anatomy|Notes and Revision": ("Head & neck anatomy: notes and revision", "تشريح الرأس والعنق: ملاحظات ومراجعة"),
    "Medicine and Medically Compromised Patients|Cardiovascular and Stroke": ("Cardiovascular disease & stroke", "أمراض القلب والأوعية والسكتة الدماغية"),
    "Medicine and Medically Compromised Patients|Clinical Skills": ("Measuring blood pressure", "قياس ضغط الدم"),
    "Medicine and Medically Compromised Patients|Corticosteroids": ("Systemic corticosteroid therapy", "العلاج الجهازي بالكورتيكوستيرويد"),
    "Medicine and Medically Compromised Patients|Diabetes": ("Diabetes mellitus", "داء السكري"),
    "Medicine and Medically Compromised Patients|Endocrine and Thyroid": ("Thyroid & endocrine disease", "أمراض الغدة الدرقية والغدد الصماء"),
    "Medicine and Medically Compromised Patients|GIT and Liver": ("Gastrointestinal & liver disease", "أمراض الجهاز الهضمي والكبد"),
    "Medicine and Medically Compromised Patients|General Medicine": ("General medicine lecture series", "سلسلة محاضرات الطب الباطني"),
    "Medicine and Medically Compromised Patients|HIV": ("HIV", "فيروس نقص المناعة (HIV)"),
    "Medicine and Medically Compromised Patients|Hematology": ("Hematology & bleeding disorders", "أمراض الدم واضطرابات النزف"),
    "Medicine and Medically Compromised Patients|Medically Compromised Patients": ("The medically compromised patient", "المريض ذو الحالة الطبية الخاصة"),
    "Medicine and Medically Compromised Patients|Pregnancy": ("Dental care in pregnancy", "العناية بالأسنان أثناء الحمل"),
    "Medicine and Medically Compromised Patients|Renal": ("Renal disease", "أمراض الكلى"),
    "Neuroanatomy|Neuroanatomy Course": ("Neuroanatomy course", "كورس التشريح العصبي"),
    "Operative Dentistry and Endodontics|Endodontics": ("Endodontics: pulp & periapical disease", "علاج الجذور: أمراض اللب وما حول الذروة"),
    "Operative Dentistry and Endodontics|History Sheets": ("Conservative history sheet", "هستوري شيت الأسنان الترميمية"),
    "Operative Dentistry and Endodontics|Operative Dentistry": ("Operative dentistry & cavity preparation", "الأسنان الترميمية وتحضير الحفر"),
    "Oral Biology and Histology|Oral Histology and Morphology": ("Oral histology & tooth morphology", "هستولوجي الفم ومورفولوجيا الأسنان"),
    "Oral Medicine and Diagnosis|History Sheets": ("History sheets explained", "شرح الهستوري شيت"),
    "Oral Medicine and Diagnosis|Oral Cancer": ("Oral cancer", "سرطان الفم"),
    "Oral Medicine and Diagnosis|Oral Ulcers": ("Oral ulcers", "قرح الفم"),
    "Oral Pathology|Bone and Jaw Lesions": ("Bone & jaw lesions", "آفات العظام والفكين"),
    "Oral Pathology|Cysts and Tumours": ("Cysts & odontogenic tumours", "الأكياس والأورام السنية المنشأ"),
    "Oral Pathology|Dental Caries and Sequelae": ("Dental caries & its sequelae", "تسوّس الأسنان ومضاعفاته"),
    "Oral Pathology|Developmental Anomalies": ("Developmental anomalies", "الشذوذات النمائية"),
    "Oral Pathology|Videos": ("Oral pathology videos", "فيديوهات باثولوجيا الفم"),
    "Oral Radiology|Radiographs": ("Dental radiographs", "الصور الشعاعية السنية"),
    "Oral and Maxillofacial Surgery|Bleeding Management": ("Managing bleeding after extraction", "التعامل مع النزف بعد الخلع"),
    "Oral and Maxillofacial Surgery|Dry Socket": ("Dry socket", "التهاب السنخ الجاف"),
    "Oral and Maxillofacial Surgery|Exam Revision": ("OMFS exam revision & spotting", "مراجعة امتحان جراحة الفم والـ Spotting"),
    "Oral and Maxillofacial Surgery|Exodontia": ("Tooth extraction (exodontia)", "خلع الأسنان"),
    "Oral and Maxillofacial Surgery|Facial Palsy": ("Facial palsy & facial nerve injury", "شلل الوجه وإصابة العصب الوجهي"),
    "Oral and Maxillofacial Surgery|History and Examination": ("History & examination", "أخذ التاريخ المرضي والفحص"),
    "Oral and Maxillofacial Surgery|Implantology": ("Implantology", "زراعة الأسنان"),
    "Oral and Maxillofacial Surgery|Local Anaesthesia": ("Local anaesthesia", "التخدير الموضعي"),
    "Oral and Maxillofacial Surgery|Medical Emergencies": ("Medical emergencies in dental practice", "الطوارئ الطبية في عيادة الأسنان"),
    "Oral and Maxillofacial Surgery|Neck Swellings": ("Neck swellings & lymph nodes", "تورمات العنق والعقد اللمفاوية"),
    "Oral and Maxillofacial Surgery|Overview": ("OMFS course contents", "محتويات كورس جراحة الفم"),
    "Oral and Maxillofacial Surgery|Salivary Glands": ("Salivary gland disorders", "أمراض الغدد اللعابية"),
    "Oral and Maxillofacial Surgery|TMJ Diseases": ("TMJ diseases", "أمراض المفصل الصدغي الفكي"),
    "Oral and Maxillofacial Surgery|Trauma": ("Maxillofacial trauma", "إصابات الوجه والفكين"),
    "Oral and Maxillofacial Surgery|Trigeminal Neuralgia": ("Trigeminal neuralgia", "ألم العصب الثلاثي التوائم"),
    "Orthodontics|General": ("Orthodontics: introduction & malocclusion", "التقويم: مقدمة وسوء الإطباق"),
    "Paediatric Dentistry|History Sheets": ("Pediatric history sheet", "هستوري شيت أسنان الأطفال"),
    "Paediatric Dentistry|Pulp Therapy": ("Pulp therapy in children", "علاج اللب عند الأطفال"),
    "Periodontics|Acute Gingival Infections": ("Acute gingival infections", "التهابات اللثة الحادة"),
    "Periodontics|Etiology": ("Etiology of periodontal diseases", "مسببات أمراض اللثة"),
    "Periodontics|General": ("Periodontics: lectures & recordings", "أمراض اللثة: محاضرات وتسجيلات"),
    "Periodontics|Gingival Enlargement": ("Gingival enlargement", "تضخم اللثة"),
    "Periodontics|History Sheets": ("Periodontics history sheet", "هستوري شيت أمراض اللثة"),
    "Periodontics|Periodontitis": ("Chronic & aggressive periodontitis", "التهاب دواعم السن المزمن والعدواني"),
    "Pharmacology and Prescriptions|Prescriptions": ("Writing prescriptions: analgesics & antibiotics", "كتابة الوصفة: المسكنات والمضادات الحيوية"),
    "Physiology|General": ("Physiology: autonomic & endocrine", "الفسيولوجيا: الجهاز العصبي الذاتي والغدد الصماء"),
    "Prosthodontics|History Sheets": ("Prosthodontics history sheet", "هستوري شيت التعويضات السنية"),
}
AUDIO = {"opus", "ogg", "mp3", "aac", "m4a", "3gpp"}
KIND = {**{e: "audio" for e in AUDIO}, "mp4": "video", "pdf": "pdf", "ppt": "slides", "pptx": "slides", "pptm": "slides",
        "doc": "document", "docx": "document", "rtf": "document", "jpg": "image", "png": "image"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "item"


def natural(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def main():
    rows = list(csv.DictReader(open(ROOT / "catalog.csv", encoding="utf-8-sig")))
    mid = {}
    for m in json.load(open(ROOT / "channel/result.json", encoding="utf-8"))["messages"]:
        f = m.get("file") or m.get("photo")
        if f:
            mid.setdefault(f, m["id"])
    groups, books, used = {}, [], 0
    for r in rows:
        parts = r["dest"][len("library/"):].split("/")
        att = {"name": parts[-1], "key": "/".join(parts), "type": KIND.get(parts[-1].rsplit(".", 1)[-1].lower(), "file"),
               "size": os.path.getsize(ROOT / "channel_r2" / r["channel_path"]), "date": r["date"], "msg": mid[r["old"]]}
        if parts[0] == "Reference Books":
            books.append((parts[1], att))
        elif parts[0] not in SKIP_SUBJECTS:
            groups.setdefault((parts[0], parts[1]), []).append(att)
    lessons = []
    for (subj, topic), atts in groups.items():
        key = f"{subj}|{topic}"
        assert key in TOPICS, f"no title for {key}"
        en, ar = TOPICS[key]
        atts.sort(key=lambda a: natural(a["name"]))
        lessons.append(dict(id=f"{SUBJECTS[subj][0]}-{slug(topic)}", subject=SUBJECTS[subj][0],
                            category="exam" if topic == "Exam Revision" else "lesson",
                            title=dict(en=en, ar=ar), attachments=atts))
    for subj, att in books:
        title = re.sub(r"\s+", " ", re.sub(r"[_]+", " ", att["name"].rsplit(".", 1)[0])).strip()
        lessons.append(dict(id=f"ref-{slug(title)}", subject=SUBJECTS[subj][0], category="reference",
                            title=dict(en=title, ar=title), attachments=[att]))
    order = [v[0] for v in SUBJECTS.values()]
    lessons.sort(key=lambda l: (order.index(l["subject"]), l["category"], l["title"]["en"].lower()))
    for l in lessons:
        l["format"] = "audio" if any(a["type"] in ("audio", "video") for a in l["attachments"]) else "notes"
        l["source"] = min(a["msg"] for a in l["attachments"])
        l["icon"] = next(v[1] for v in SUBJECTS.values() if v[0] == l["subject"]) if l["category"] != "reference" else "book"
    seen = {}
    for l in lessons:  # two files can slug alike (e.g. "Dental Pulse .pdf" / "Dental Pulse.pdf")
        seen[l["id"]] = seen.get(l["id"], 0) + 1
        if seen[l["id"]] > 1:
            l["id"] += f"-{seen[l['id']]}"
    assert len({l["id"] for l in lessons}) == len(lessons), "duplicate lesson id"
    n = sum(len(l["attachments"]) for l in lessons)
    assert n == len(rows) - sum(1 for r in rows if r["dest"].startswith("library/Channel Posts")), n
    subjects = [dict(id=v[0], icon=v[1], tone=v[2], en=v[3], ar=v[4]) for v in SUBJECTS.values()
                if any(l["subject"] == v[0] for l in lessons)]
    out = ROOT / "src/data/library.mjs"
    out.write_text("// generated by build_library.py from catalog.csv - do not edit by hand\n"
                   f"export const subjects = {json.dumps(subjects, ensure_ascii=False)};\n"
                   f"export const lessons = {json.dumps(lessons, ensure_ascii=False)};\n", encoding="utf-8")
    cat = {c: sum(1 for l in lessons if l["category"] == c) for c in ("lesson", "reference", "exam")}
    print(f"{len(subjects)} subjects, {len(lessons)} lessons {cat}, {n} attachments, {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
