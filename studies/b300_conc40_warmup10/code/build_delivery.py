import csv
import hashlib
import shutil
import zipfile
from pathlib import Path

BASE = Path("/tmp/b300_conc40_analysis")
OUT = BASE / "output"
DELIVERY = BASE / "delivery"
PKG = DELIVERY / "InferenceX_MiniMax_M3_B300_Conc40_AgentX_package"
REPORT_NAME = "InferenceX_MiniMax_M3_B300_Conc40_AgentX_full_result_ko.md"
ZIP_NAME = "InferenceX_MiniMax_M3_B300_Conc40_AgentX_analysis_bundle.zip"

DELIVERY.mkdir(parents=True, exist_ok=True)
if PKG.exists():
    shutil.rmtree(PKG)
(PKG / "outputs").mkdir(parents=True)
(PKG / "code").mkdir(parents=True)


def read(path):
    return Path(path).read_text(encoding="utf-8")


def fenced(title, body, language="text"):
    return f"## {title}\n\n```{language}\n{body.rstrip()}\n```\n"


phase_csv = read(OUT / "03_phase_counts.csv")
dist_csv = read(OUT / "07_warmup_distribution.csv")
main_report = read(OUT / "09_final_analysis_ko.md")
main_report = main_report.replace("# B300 Conc40", "## B300 Conc40", 1).replace("\n## ", "\n### ")
schema = read(OUT / "02_schema_summary.txt")
source_evidence = read(OUT / "08_aiperf_818c3a5a_source_evidence.md")
source_evidence = source_evidence.replace(
    "# AIPerf 818c3a5a source evidence", "### AIPerf 818c3a5a source evidence", 1
).replace("\n## ", "\n#### ")
inventory = read(OUT / "01_artifact_inventory.txt")

csv_counts = []
for name in [
    "03_phase_counts.csv",
    "04_initial40_root_summary.csv",
    "05_recycled_root_summary.csv",
    "06_warmup_request_detail.csv",
    "07_warmup_distribution.csv",
]:
    with (OUT / name).open(encoding="utf-8", newline="") as f:
        csv_counts.append((name, sum(1 for _ in csv.DictReader(f))))

report = f"""# InferenceX MiniMax-M3 B300 Conc40 AgentX — 전체 수행 결과

이 문서는 GitHub Actions run `30849838984`의 지정 공개 artifact와 InferenceX commit `8767d90c11860a10668f2d66179711a9c24fc8bd`, AIPerf gitlink `818c3a5a2922c535af6271ff296ed374e292b8e4`, 공개 corpus revision `23f152f6f0f9399a85901b89a6458def0ef16729`를 기준으로 작성한 단일 통합 보고서다.

- Repository/workspace 파일 수정·commit·push 없음
- Raw prompt/response 본문 출력 없음
- Artifact ZIP SHA-256 검증 완료
- Initial/recycled root 94개 모두 source total 해결; `UNRESOLVED` 없음
- `gh auth status`의 저장 토큰은 무효였으며, 설치된 signed-in GitHub connector를 통해 동일 공개 artifact를 다운로드함

{main_report}

---

## 부록 A. Request JSONL schema 및 identity/index 규칙

```text
{schema.rstrip()}
```

---

## 부록 B. Historical AIPerf 818c3a5a 구현 근거

{source_evidence}

---

{fenced("부록 C. Phase counts CSV", phase_csv, "csv")}

{fenced("부록 D. Warmup distribution CSV", dist_csv, "csv")}

---

## 부록 E. CSV 행 수

| 파일 | data rows |
|---|---:|
{chr(10).join(f"| `{name}` | {count} |" for name, count in csv_counts)}

---

{fenced("부록 F. Artifact inventory 및 digest", inventory, "text")}

---

## 부록 G. 재현 코드

ZIP의 `code/`에는 다음 분석 코드가 포함된다.

- `generate_outputs.py`: public corpus provenance 결합, initial/recycled 분류, 9개 산출물 생성
- `scan_profile.py`: recursive phase/schema/identity frequency scan
- `inspect_corpus_structure.py`: Weka outer/nested request 구조 검사
- `quick_initial.py`: artifact log initial-lane 표와 request counts 교차검사
- `build_delivery.py`: 통합 Markdown 및 검증 manifest/ZIP 생성

코드는 `/tmp/b300_conc40_analysis/`의 다운로드 자료를 입력으로 사용한다. Raw artifact와 500MB corpus prefix 자체는 ZIP 크기를 불필요하게 키우므로 제외했으며, 필요한 artifact/corpus identity와 digest는 본 문서와 inventory에 고정되어 있다.
"""

standalone = DELIVERY / REPORT_NAME
standalone.write_text(report, encoding="utf-8")
(PKG / REPORT_NAME).write_text(report, encoding="utf-8")

for path in sorted(OUT.iterdir()):
    if path.is_file():
        shutil.copy2(path, PKG / "outputs" / path.name)

for name in [
    "generate_outputs.py",
    "scan_profile.py",
    "inspect_corpus_structure.py",
    "quick_initial.py",
    "build_delivery.py",
]:
    shutil.copy2(BASE / name, PKG / "code" / name)

manifest = """InferenceX MiniMax-M3 B300 Conc40 AgentX analysis bundle

Top-level integrated report:
  InferenceX_MiniMax_M3_B300_Conc40_AgentX_full_result_ko.md

outputs/:
  01_artifact_inventory.txt
  02_schema_summary.txt
  03_phase_counts.csv
  04_initial40_root_summary.csv
  05_recycled_root_summary.csv
  06_warmup_request_detail.csv
  07_warmup_distribution.csv
  08_aiperf_818c3a5a_source_evidence.md
  09_final_analysis_ko.md

code/:
  generate_outputs.py
  scan_profile.py
  inspect_corpus_structure.py
  quick_initial.py
  build_delivery.py

Excluded intentionally:
  Raw GitHub artifact ZIP and extracted large metric files
  Public corpus raw/prefix data
  Any private/internal logs or credentials
"""
(PKG / "PACKAGE_MANIFEST.txt").write_text(manifest, encoding="utf-8")

sum_lines = []
for path in sorted(p for p in PKG.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt"):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    sum_lines.append(f"{digest}  {path.relative_to(PKG)}")
(PKG / "SHA256SUMS.txt").write_text("\n".join(sum_lines) + "\n", encoding="utf-8")

zip_path = DELIVERY / ZIP_NAME
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for path in sorted(p for p in PKG.rglob("*") if p.is_file()):
        zf.write(path, Path(PKG.name) / path.relative_to(PKG))

zip_sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
print(f"report={standalone}")
print(f"report_size={standalone.stat().st_size}")
print(f"zip={zip_path}")
print(f"zip_size={zip_path.stat().st_size}")
print(f"zip_sha256={zip_sha}")
