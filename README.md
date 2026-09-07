# 마인토피아 TerritoryWar — 레퍼런스

마인크래프트 위에 올린 타일 기반 실시간 전략 플러그인의 문서 사이트입니다.
소개, 조작법, 종족별 설명, 그리고 **건물 50종 · 병종 102종의 개별 페이지**가 들어 있습니다.

**→ https://remotekar.github.io/territory-war/**

## 이 레포에 있는 것

| 경로 | 무엇 |
|---|---|
| `docs/` | 완성된 사이트. GitHub Pages 가 이 폴더를 그대로 서빙합니다. |
| `data/docs.json` | 게임이 뱉은 원본 데이터. 사이트의 모든 수치가 여기서 나옵니다. |
| `build.py` | `data/docs.json` → `docs/` 생성기. 의존성 없음. |
| `tools/diagnose.py` | 손으로 쓴 문구를 AI 티 분류 체계로 채점합니다. |

플러그인 소스 코드는 여기 없습니다. 문서와 그 원본 데이터만 있습니다.

## 어떻게 만들어지나

문서를 손으로 쓰면 밸런스를 만질 때마다 게임과 어긋납니다. 그래서 규칙은 한 군데에만
둡니다 — 게임 안에.

```
서버 콘솔에서:   tw docs        →  plugins/TerritoryWar/docs.json
이 레포에서:     cp …/docs.json data/docs.json
                python build.py →  docs/
```

`tw docs` 는 플러그인이 자기 enum 을 순회하면서 JSON 을 쓰는 콘솔 전용 명령입니다.
소스 파일을 정규식으로 긁지 않고 **돌아가는 게임에 물어보는** 이유는, 문서가 알고 싶어 하는
값의 절반이 계산 결과라서입니다.

- 병종의 공격력은 생성자에 적힌 `damage` 가 아니라 `damage()` 입니다
- 강화 비용은 올라갈 레벨에 따라 달라집니다
- 망루의 주둔 인원은 자기 레벨과 함께 늘어납니다
- 어느 종족이 어느 건물을 지을 수 있는지는 네 개의 집합을 정해진 순서로 물어본 결과입니다

파서는 필드는 가져와도 이것들을 전부 놓치는데, 하필 놓치는 쪽이 플레이어가 실제로
계산에 쓰는 숫자입니다.

## 문구 검증

사람이 쓴 문장은 `tools/diagnose.py` 로 채점합니다.
[humanize-korean](https://github.com/epoko77-ai/im-not-ai) 의 분류 체계와 실측 지표를
그대로 빌려 씁니다.

```bash
git clone --depth 1 https://github.com/epoko77-ai/im-not-ai
python tools/diagnose.py --skill ./im-not-ai
```

| 지표 | 처음 | 지금 | 기준 |
|---|---|---|---|
| C-11 연결어미 뒤 쉼표 | 0.600 | **0.059** | 인간 0.041 · AI 0.198 |
| C-8 대구 | 1 | **0** | 사람 코퍼스 0건 |
| E-2 종결어미 다양도 | 0.065 | **0.745** | 높을수록 좋음 |
| E-2 '다' 연속 4+ 구간 | 5 | **3** | 0 이 목표 |

C-11 이 분류 체계에서 가장 강한 단일 신호인데 처음 재보니 0.600 이 나왔습니다.
AI 평균의 세 배입니다. "세우고, 나누고," 처럼 연결어미마다 쉼표를 박는 영어 습관이
원인이었고, 그것만 걷어내도 인간 기준선 근처까지 내려갑니다.

E-2 는 문체를 바꿔서 풀었습니다. 합니다체는 모든 문장이 '다'로 끝나 문서 전체가
하나의 긴 연속이 됩니다. 평서체로 옮기니 `한다·이다·린다·없다` 로 종결이 갈리면서
다양도가 열한 배가 됐습니다.

게임에서 가져온 문장(종족 소개, 건물 설명)은 손대지 않습니다. 그쪽은 인게임에도
그대로 뜨는 텍스트라 게임의 말투를 유지합니다.

## 다시 만들기

```bash
python build.py     # -> docs/
```

파이썬 3 표준 라이브러리만 씁니다. 결과물은 정적 HTML/CSS 이고, 목록 페이지의 검색·종족
필터에만 인라인 스크립트가 조금 붙습니다.

## 데이터를 직접 쓰고 싶다면

`docs.json` 은 사이트에도 그대로 올라가 있어서 바로 가져다 쓸 수 있습니다.

```
https://remotekar.github.io/territory-war/docs.json
```

```jsonc
{
  "generated": "…",
  "races":     [ { "id", "korean", "blurb", "armoury", "quarters",
                   "researches", "buildings": [], "units": [], "policies": [] } ],
  "buildings": [ { "id", "korean", "purpose", "tiles", "maxHp", "cost",
                   "wing", "scale", "placeable", "upgradeCosts": [],
                   "raisableBy": [], "trains": [] } ],
  "units":     [ { "id", "korean", "role", "tier", "maxHp", "damage", "range",
                   "cost", "trainedAt", "requiredArmoury", "owner", "limits": [],
                   "requirement": {}, "fieldableBy": [],
                   "strongAgainst": [], "weakAgainst": [] } ],
  "armouryResearch": [], "labs": [], "doctrines": []
}
```

`requirement` 가 종족별 객체인 것은 같은 조건이라도 종족마다 다른 건물을 가리키기
때문입니다. 위더의 요구 조건은 이방인에게는 "무기고 Lv4" 지만 피글린에게는
"괴수 우리 Lv4" 입니다 — 피글린은 무기고를 지을 수 없습니다.
