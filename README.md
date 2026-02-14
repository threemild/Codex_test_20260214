# 지역별 차량 법규 QA 에이전트 (초보자용)

좋아요. **개발을 잘 몰라도 바로 따라할 수 있게** 설명할게요.  
이 도구는 다음을 해줍니다.

1. 법규 PDF를 읽어서
2. 검색 가능한 DB(SQLite)에 넣고
3. 질문하면 관련 조항을 찾아서 보여줍니다.

---

## 0) 이 프로젝트로 할 수 있는 일

예: "한국(KR) 전기차 배터리 안전 관련 필수 시험 항목은?" 같은 질문을 하면,
- DB에서 관련 조항을 찾아
- 조항 제목/페이지와 함께 근거를 보여주고
- (선택) OpenAI API 키가 있으면 요약 답변도 생성합니다.

---

## 1) 딱 3개만 기억하세요

- `src/ingest.py` : PDF를 DB에 넣는 도구
- `src/query.py` : 질문하는 도구
- `schema.sql` : DB 구조

---

## 2) 완전 초보용 따라하기 (복붙용)

> 아래는 **Linux/macOS bash 기준**입니다.

### 2-1. 가상환경 만들기 + 패키지 설치
```bash
cd /workspace/Codex_test_20260214
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2-2. DB 초기화(처음 1번만)
```bash
python src/ingest.py init --db regulations.db
```

정상이라면:
```text
database initialized
```

### 2-3. 법규 PDF 넣기
예시(파일명은 본인 파일로 변경):
```bash
python src/ingest.py ingest \
  --db regulations.db \
  --pdf ./data/korea_emission_rule.pdf \
  --region KR \
  --authority "환경부" \
  --title "대기환경보전법 시행규칙" \
  --effective-date 2024-01-01
```

정상이라면:
```text
ingested regulation_id=..., chunks=...
```

### 2-4. 질문하기
```bash
python src/query.py ask \
  --db regulations.db \
  --question "한국에서 전기차 배터리 안전 관련 필수 시험 항목은?" \
  --region KR
```

출력은 2개 블록이 나옵니다.
- `=== 검색 근거 ===` : 찾은 조항 목록
- `=== 초안 답변 ===` : 답변(키가 없으면 근거 위주 안내)

---

## 3) 폴더 준비 예시

PDF는 예를 들어 이렇게 두세요.

```text
/workspace/Codex_test_20260214/
  data/
    korea_emission_rule.pdf
```

`data` 폴더가 없으면 먼저:
```bash
mkdir -p data
```

---

## 4) OpenAI 요약 답변까지 쓰고 싶다면 (선택)

API 키를 환경변수로 설정:
```bash
export OPENAI_API_KEY="여기에_본인키"
```

그 다음 같은 `ask` 명령을 실행하면,
근거를 바탕으로 요약 답변이 추가됩니다.

---

## 5) 지역별 운영 팁 (실무용)

실무에서는 PDF 넣을 때 아래 규칙으로 관리하면 좋습니다.

- `--region` : `KR`, `EU`, `US-CA` 같이 표준화
- `--title` : 법규명 + 버전(개정일)
- `--effective-date` : 시행일 정확히 입력

예:
```bash
python src/ingest.py ingest \
  --db regulations.db \
  --pdf ./data/eu_battery_regulation.pdf \
  --region EU \
  --authority "European Commission" \
  --title "EU Battery Regulation" \
  --effective-date 2025-08-18
```

---

## 6) 자주 나는 오류

### Q1. `No module named pypdf`
A. 가상환경 활성화 후 `pip install -r requirements.txt` 다시 실행하세요.

### Q2. `OPENAI_API_KEY가 없어 원문 근거만 반환합니다.`
A. 정상 동작입니다. 키가 없으면 검색 결과만 보여줍니다.

### Q3. 검색이 잘 안 맞아요
A. 같은 의미의 키워드로 짧게 바꿔서 질문해보세요.
예: "배터리 안전" / "절연 저항 시험" / "충돌 후 안전" 등.

---

## 7) 지금 단계에서 한계

이 프로젝트는 **스타터 버전**이라 다음은 아직 단순합니다.

- 조/항/호 구조 파싱이 정교하지 않음
- FTS(키워드 검색)만 사용, 임베딩 검색 미적용
- 차량 타입(M1/N1 등)에 따른 자동 적용성 판단 미구현

---

## 8) 다음 단계(원하면 제가 이어서 만들어드릴 수 있음)

1. PDF 업로드 웹 화면(드래그앤드롭)
2. "차종/시장" 입력하면 적용 법규 자동 추천
3. 답변마다 인용 조항/페이지 고정 출력
4. 개정 이력(시행일 기준) 비교 리포트

---

## 면책

본 도구는 법률 자문이 아닌 **기술적 검색 보조**입니다.  
최종 의사결정 전 원문 확인 및 법무 검토가 필요합니다.
