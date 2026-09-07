# -*- coding: utf-8 -*-
"""Builds the reference site out of the game's own dump.

Nothing here knows a rule. Every number, name and sentence on the finished pages comes
from data/docs.json, which the plugin writes with `tw docs` on the console - so a balance
change is one dump and one run away from being on the site, and there is no second copy of
the rules to drift out of step with the first.

    python build.py            # -> docs/
"""
import html
import json
import io
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs")
DATA = os.path.join(HERE, "data", "docs.json")

RACE_ORDER = ["OUTLANDER", "VILLAGER", "UNDEAD", "PIGLIN"]
RACE_TAG = {"OUTLANDER": "out", "VILLAGER": "vil", "UNDEAD": "und", "PIGLIN": "pig"}

NAV = [
    ("index.html", "소개"),
    ("controls.html", "조작"),
    ("races.html", "종족"),
    ("buildings.html", "건물"),
    ("units.html", "병종"),
    ("research.html", "연구"),
]


def e(s):
    return html.escape(str(s if s is not None else ""))


def page(rel_depth, title, body, active):
    """One HTML file. rel_depth is how many directories deep it sits."""
    up = "../" * rel_depth
    nav = "".join(
        '<a href="%s%s"%s>%s</a>' % (up, href, ' class="on"' if href == active else "", label)
        for href, label in NAV
    )
    return """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s · 마인토피아 TerritoryWar</title>
<link rel="stylesheet" href="%sassets/style.css">
</head>
<body>
<header>
  <a class="brand" href="%sindex.html">마인토피아 <b>TerritoryWar</b></a>
  <nav>%s</nav>
</header>
<main>
%s
</main>
<footer>
  타일 기반 실시간 전략 · 마인크래프트 플러그인 ·
  이 페이지의 모든 수치는 게임 데이터에서 자동 생성됩니다
</footer>
</body>
</html>
""" % (e(title), up, up, nav, body)


def cost(c):
    bits = []
    if c["ore"]:
        bits.append('<span class="r ore">광물 %d</span>' % c["ore"])
    if c["food"]:
        bits.append('<span class="r food">식량 %d</span>' % c["food"])
    if c["wood"]:
        bits.append('<span class="r wood">목재 %d</span>' % c["wood"])
    return " ".join(bits) if bits else '<span class="muted">무료</span>'


def race_pills(ids, up=""):
    return "".join(
        '<a class="pill %s" href="%srace/%s.html">%s</a>' % (RACE_TAG[r], up, r, RACE_KOR[r])
        for r in ids
    )


# ---------------------------------------------------------------- pages
def build():
    doc = json.load(io.open(DATA, encoding="utf-8"))
    global RACE_KOR
    RACE_KOR = {r["id"]: r["korean"] for r in doc["races"]}
    races = {r["id"]: r for r in doc["races"]}
    builds = {b["id"]: b for b in doc["buildings"]}
    units = {u["id"]: u for u in doc["units"]}

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for d in ["", "race", "building", "unit", "assets"]:
        os.makedirs(os.path.join(OUT, d), exist_ok=True)

    write("assets/style.css", CSS, raw=True)
    write(".nojekyll", "", raw=True)
    shutil.copy(DATA, os.path.join(OUT, "docs.json"))

    index(doc)
    controls()
    race_index(doc)
    for r in doc["races"]:
        race_page(r, builds, units)
    listing_buildings(doc, units)
    for b in doc["buildings"]:
        building_page(b, units)
    listing_units(doc)
    for u in doc["units"]:
        unit_page(u, builds)
    research(doc)

    n = sum(len(f) for _, _, f in os.walk(OUT))
    print("built %d files into %s" % (n, OUT))


def write(rel, content, raw=False):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(content)


# ---------------------------------------------------------------- index
def index(doc):
    cards = ""
    for r in doc["races"]:
        cards += """
    <a class="card %s" href="race/%s.html">
      <h3>%s</h3>
      <p>%s</p>
      <div class="stat"><span>건물 %d</span><span>병종 %d</span></div>
    </a>""" % (RACE_TAG[r["id"]], r["id"], e(r["korean"]), e(r["blurb"]),
               len(r["buildings"]), len(r["units"]))

    body = """
<section class="hero">
  <h1>영토 전쟁</h1>
  <p class="lead">
    마인크래프트 위에 올린 타일 기반 실시간 전략. 땅을 점유해 정착지를 세우고,
    인구를 노동과 병력으로 나누고, 원정대를 꾸려 남의 땅으로 나갑니다.
    타운홀이 무너지면 그 나라는 끝입니다.
  </p>
  <div class="cta">
    <a class="btn" href="controls.html">조작부터 보기</a>
    <a class="btn ghost" href="races.html">종족 고르기</a>
  </div>
</section>

<section>
  <h2>네 개의 종족</h2>
  <p class="sub">같은 지도를 전혀 다른 방식으로 삽니다. 고르는 순간 지을 수 있는 건물과
     뽑을 수 있는 병종이 갈립니다.</p>
  <div class="cards">%s</div>
</section>

<section>
  <h2>한 판의 흐름</h2>
  <ol class="flow">
    <li><b>정착</b> 필드맵에서 칸을 점유하고 타운홀을 세웁니다.</li>
    <li><b>경제</b> 인구를 인부로 보내 광물·식량·목재를 캡니다.
        인력 배분(<kbd>6</kbd>)이 건설과 생산의 비율입니다.</li>
    <li><b>확장</b> 집으로 인구 한도를 올리고, 생산 건물을 강화합니다.</li>
    <li><b>군비</b> 무기고 계열 레벨이 병종 티어를 엽니다.
        연구는 능력치, 건물 레벨은 해금입니다.</li>
    <li><b>원정</b> 출진 창에서 병력과 보급을 실어 내보냅니다.
        보급이 떨어지면 굶습니다.</li>
    <li><b>결착</b> 상대 타운홀을 부수거나, 외교로 항복을 받아냅니다.</li>
  </ol>
</section>

<section class="grid2">
  <div>
    <h2>알아둘 것</h2>
    <ul class="plain">
      <li>인구는 노동이자 병력입니다. 징집하면 그만큼 생산이 줍니다.</li>
      <li>병종은 상성이 있습니다. 창병은 기병에게 강하고 경보병에게 약합니다.</li>
      <li>지형 특산 병종·건물이 있습니다. 그 지형을 점유해야 열립니다.</li>
      <li>장벽은 실제 블록이 아니라 길막이입니다. 전투 중인 칸에는 세울 수 없습니다.</li>
    </ul>
  </div>
  <div>
    <h2>데이터</h2>
    <ul class="plain">
      <li>이 사이트의 표와 수치는 전부 <code>docs.json</code> 에서 생성됩니다.</li>
      <li>서버 콘솔에서 <code>tw docs</code> 를 실행하면 갱신본이 나옵니다.</li>
      <li><a href="docs.json">docs.json 내려받기</a></li>
    </ul>
    <p class="muted small">생성 시각 %s</p>
  </div>
</section>
""" % (cards, e(doc["generated"]))
    write("index.html", page(0, "소개", body, "index.html"))


# ---------------------------------------------------------------- controls
def controls():
    """The command tables here were checked one by one against TwCommand's dispatcher.

    They were first lifted out of the in-game help text, which turned out to be a
    different list: the help page has never mentioned `/tw preset`, and starting a nation
    does not work without it.
    """
    def row(k, name, note):
        return "<tr><td><kbd>%s</kbd></td><td><b>%s</b></td><td>%s</td></tr>" % (k, name, note)

    def clist(rows):
        return "".join("<tr><td><code>%s</code></td><td>%s</td></tr>" % (c, d)
                       for c, d in rows)

    starting = [
        ("/tw preset", "국가 이름·색·문양·<b>종족</b>을 고릅니다. 한 번만 하면 됩니다"),
        ("/tw join", "참전. 별칭은 <code>/tw play</code> · <code>/tw 참가</code>"),
        ("우클릭", "정착지 선정 단계에 땅을 우클릭해 자리를 잡습니다"),
        ("/tw watch", "관전으로 들어갑니다. 참전 중에는 바꿀 수 없습니다"),
        ("/tw phase", "현재 단계와 남은 시간"),
    ]
    idle = "".join([
        row("1", "필드맵 / 정착지 전환", "영토·요새·원정대를 보러 나갑니다"),
        row("2", "건물 건설", "고른 뒤 지을 곳을 조준합니다"),
        row("3", "외교", "동맹 · 항복 · 지원"),
        row("4", "출진", "병력과 보급을 실어 내보냅니다"),
        row("5", "국가 정보", "자원·인구·정책·기술을 한 창에서"),
        row("6", "인력 배분", "건설에 나가는 인력, 나머지는 생산 건물로"),
        row("8", "다른 정착지", "내 정착지 사이를 오갑니다"),
    ])
    sel = "".join([
        row("1", "강화 / 취소", "레벨을 올립니다. 진행 중이면 취소하고 자원을 전액 돌려받습니다"),
        row("2", "전용 창", "건물마다 다릅니다 — 병종 생산, 연구, 주둔, 민병 무장"),
        row("3", "보조 창", "괴수 우리의 연구, 망루의 주둔 해제"),
        row("4", "상세 정보", "능력치와 상성을 봅니다"),
        row("5", "인부 우선순위", "생산 건물에 사람을 먼저 보낼 순서"),
    ])
    field = "".join([
        row("1", "정착지로", "필드맵에서 돌아옵니다"),
        row("2", "원정대 목록", "짐과 굶주림까지 봅니다"),
        row("3", "보급 · 교역", "정착지에서 물자를 싣고 내립니다"),
        row("4", "귀환 · 해산", ""),
        row("6", "필드 건설", "전초기지·보급기지 같은 야전 건물"),
    ])

    cmds = [
        ("/tw info", "내 나라 요약"),
        ("/tw here", "서 있는 칸 정보"),
        ("/tw list", "나라 목록"),
        ("/tw build [건물]", "인수 없이 쓰면 건설 창이 열립니다"),
        ("/tw claim / unclaim", "칸 점유 / 해제"),
        ("/tw upgrade", "서 있는 건물 강화"),
        ("/tw train [병종] [수]", "인수 없이 치면 내 종족의 병종표"),
        ("/tw garrison [병종]", "서 있는 망루·발리스타에 주둔"),
        ("/tw sortie", "출진 창 (병종·보급 슬라이더)"),
        ("/tw armies", "원정대 목록 (짐·굶주림 포함)"),
        ("/tw follow", "선택한 원정대 위치로 이동"),
        ("/tw recallarmy", "선택한 원정대 정지"),
        ("/tw trade", "선택한 원정대로 정착지에서 거래"),
        ("/tw pack [reload]", "리소스팩 상태 / 재전송"),
        ("/tw 설정", "라운드 규칙 보기·변경"),
    ]
    war = [
        ("/tw siege &lt;국가&gt;", "상대 타운홀 방향으로 바위를 던집니다. 광물 15, 물리 탄도 — "
                              "튕기고 굴러서 <b>멈춘 칸의 건물</b>이 맞습니다"),
        ("/tw diplomacy", "외교 창 (동맹·항복·지원)"),
        ("/tw ally &lt;국가&gt;", "동맹 제안 (이미 동맹이면 파기)"),
        ("/tw surrender &lt;국가&gt;", "항복 제안 (비축 절반 배상 + 속국화)"),
        ("/tw accept &lt;국가&gt;", "받은 제안 수락"),
        ("/tw offers", "받은 제안 목록"),
        ("/tw gift &lt;국가&gt; &lt;자원&gt; &lt;수량&gt;", "자원 지원"),
        ("/tw 비난 &lt;국가&gt;", "공개 규탄 — 실질 효과는 없습니다"),
    ]
    admin = [
        ("/tw start [초]", "정착지 선정 시작"),
        ("/tw 치트 시작 [국가명]", "대기·선정 건너뛰고 즉시 정착지 생성"),
        ("/tw 치트 자원 [양]", "광물·식량·목재를 그만큼 (기본 1000)"),
        ("/tw 치트 완공", "건설·강화 즉시 완료"),
        ("/tw 치트 유닛 &lt;병종&gt; [수]", "즉시 생성 (비용·훈련 무시)"),
        ("/tw 치트 적 &lt;병종&gt; [수]", "적대 AI 병사 생성"),
        ("/tw 치트 적정리", "생성한 적을 전부 지웁니다"),
        ("/tw 치트 전투 [규모]", "모의전 — 검병:궁수:창기병 = 60:20:10"),
        ("/tw 치트 배속 [배]", "경제 속도"),
        ("/tw 설정 인구 &lt;최대&gt;", "0 이면 무제한"),
        ("/tw 설정 정예 &lt;수&gt;", "5티어 병종 동시 보유 상한"),
        ("/tw 설정 리로드", "config.yml 을 재시작 없이 다시 읽습니다"),
        ("/tw 래그돌 [무손상|팔|덩어리|산산조각]", "바라보는 곳에 시체 하나"),
        ("/tw 샌드박스", "모델 전시장"),
        ("/tw 트림", "갑옷 트림 목록"),
        ("/tw 스킨목록 · /tw 스킨 &lt;이름&gt;", "마네킹 스킨 목록·미리보기"),
        ("tw docs", "콘솔 전용 — 이 문서의 원본 데이터를 씁니다"),
    ]

    body = """
<h1>조작</h1>
<p class="sub">거의 모든 조작은 핫바에서 이뤄집니다. 무엇을 선택했느냐에 따라 같은 숫자 키가
   다른 일을 합니다.</p>

<section>
  <h2>시작하기</h2>
  <p class="sub">순서대로 하면 됩니다. <code>/tw nation</code> 은 폐지됐고,
     건국은 <b>preset 한 번 + join</b> 입니다.</p>
  <table class="cmds"><tbody>%s</tbody></table>
</section>

<section>
  <h2>아무것도 선택하지 않았을 때</h2>
  <table class="keys"><tbody>%s</tbody></table>
</section>

<section>
  <h2>건물을 선택했을 때</h2>
  <p class="sub">건물을 바라보고 좌클릭하면 선택됩니다.</p>
  <table class="keys"><tbody>%s</tbody></table>
</section>

<section>
  <h2>필드맵에서</h2>
  <table class="keys"><tbody>%s</tbody></table>
</section>

<section>
  <h2>명령어</h2>
  <table class="cmds"><tbody>%s</tbody></table>
</section>

<section>
  <h2>전쟁과 외교</h2>
  <table class="cmds"><tbody>%s</tbody></table>
</section>

<section>
  <h2>관리자 · 테스트</h2>
  <table class="cmds"><tbody>%s</tbody></table>
</section>
""" % (clist(starting), idle, sel, field, clist(cmds), clist(war), clist(admin))
    write("controls.html", page(0, "조작", body, "controls.html"))


# ---------------------------------------------------------------- races
def race_index(doc):
    cards = ""
    for r in doc["races"]:
        cards += """
    <a class="card %s" href="race/%s.html">
      <h3>%s</h3>
      <p>%s</p>
      <div class="stat"><span>건물 %d</span><span>병종 %d</span><span>정책 %d</span></div>
    </a>""" % (RACE_TAG[r["id"]], r["id"], e(r["korean"]), e(r["blurb"]),
               len(r["buildings"]), len(r["units"]), len(r["policies"]))
    body = """
<h1>종족</h1>
<p class="sub">고르는 순간 지을 수 있는 건물과 뽑을 수 있는 병종이 갈립니다.
   경제 방식도 다릅니다 — 어떤 종족은 농사를 짓고, 어떤 종족은 포로를 잡습니다.</p>
<div class="cards">%s</div>
""" % cards
    write("races.html", page(0, "종족", body, "races.html"))


def race_page(r, builds, units):
    rid = r["id"]
    facts = [
        ("무기고 계열", builds[r["armoury"]]["korean"], "병종 티어를 여는 건물"),
        ("주거 계열", builds[r["quarters"]]["korean"], "인구 한도를 올리는 건물"),
        ("연구소", "가능" if r["researches"] else "불가",
         "연구소를 못 짓는 종족은 연구 요구 없이 모든 건물이 Lv4까지 갑니다"),
        ("민간인", "있음" if r["keepsCivilians"] else "없음",
         "민간인이 없으면 징집이 아니라 값을 치러 병력을 얻습니다"),
        ("자연 증가", "있음" if r["growsOnItsOwn"] else "없음", ""),
        ("시체 수급", "있음" if r["reapsRemains"] else "없음", ""),
        ("식량 소모", "x%s" % r["ration"], "병사 한 명당 배급 배율"),
    ]
    ft = "".join("<tr><th>%s</th><td><b>%s</b></td><td class='muted'>%s</td></tr>"
                 % (e(a), e(b), e(c)) for a, b, c in facts)

    def bgroup(ids):
        return "".join(
            '<a class="chip" href="../building/%s.html">%s</a>' % (i, e(builds[i]["korean"]))
            for i in ids)

    ulist = ""
    for tier in range(1, 6):
        row = [i for i in r["units"] if units[i]["tier"] == tier]
        if not row:
            continue
        ulist += '<div class="tier"><span class="t">T%d</span>%s</div>' % (
            tier, "".join('<a class="chip" href="../unit/%s.html">%s</a>' % (i, e(units[i]["korean"]))
                          for i in row))

    pol = ""
    for p in r["policies"]:
        pol += "<tr><td class='muted'>%s</td><td><b>%s</b></td><td>%s</td></tr>" % (
            e(p["group"]), e(p["korean"]), e(p["effect"]))

    body = """
<p class="crumb"><a href="../races.html">종족</a> / %s</p>
<h1 class="%s">%s</h1>
<p class="lead">%s</p>

<section><h2>기본기</h2><table class="facts"><tbody>%s</tbody></table></section>

<section><h2>지을 수 있는 건물 <span class="muted">%d</span></h2>
  <div class="chips">%s</div></section>

<section><h2>뽑을 수 있는 병종 <span class="muted">%d</span></h2>
  %s</section>

<section><h2>정책 <span class="muted">%d</span></h2>
  <table class="cmds"><tbody>%s</tbody></table></section>
""" % (e(r["korean"]), RACE_TAG[rid], e(r["korean"]), e(r["blurb"]), ft,
       len(r["buildings"]), bgroup(r["buildings"]),
       len(r["units"]), ulist or '<p class="muted">훈련으로 얻는 병종이 없습니다.</p>',
       len(r["policies"]), pol or "<tr><td class='muted'>정책을 고르지 않는 종족입니다.</td></tr>")
    write("race/%s.html" % rid, page(1, r["korean"], body, "races.html"))


# ---------------------------------------------------------------- buildings
def listing_buildings(doc, units):
    # The halls and the round's furniture are not on any build menu, so they are not on
    # this list either - see Docs.placeable. They keep their own pages.
    shown = [b for b in doc["buildings"] if b["placeable"]]
    rows = ""
    for b in sorted(shown, key=lambda x: (x["scale"], x["wing"], x["korean"])):
        rows += """
    <tr data-races="%s" data-name="%s">
      <td><a href="building/%s.html">%s</a></td>
      <td class="muted small">%s</td>
      <td>%s</td>
      <td class="num">%d칸</td>
      <td class="num">%d</td>
      <td>%s</td>
      <td class="pills">%s</td>
    </tr>""" % (" ".join(b["raisableBy"]), e(b["korean"]), b["id"], e(b["korean"]),
                e(b["wing"]), e(b["purpose"]), b["tiles"], b["maxHp"], cost(b["cost"]),
                race_pills(b["raisableBy"], ""))
    halls = "".join(
        '<a class="chip" href="building/%s.html">%s</a>' % (b["id"], e(b["korean"]))
        for b in doc["buildings"] if b["hall"])
    body = """
<h1>건물 <span class="muted">%d</span></h1>
<p class="sub">칸은 차지하는 타일 수, 체력은 부서지기까지의 내구입니다.
   종족 뱃지는 그 건물을 지을 수 있는 종족입니다.</p>
%s
<table class="list" id="tbl">
<thead><tr><th>이름</th><th>분류</th><th>쓰임</th><th class="num">크기</th><th class="num">체력</th>
<th>건설 비용</th><th>종족</th></tr></thead>
<tbody>%s</tbody></table>
%s
<section><h2>정착지 중심</h2>
<p class="sub">건설 메뉴에는 없습니다. 정착지와 함께 생기고, 무너지면 그 나라가 끝납니다.</p>
<div class="chips">%s</div></section>
""" % (len(shown), FILTER, rows, FILTER_JS, halls)
    write("buildings.html", page(0, "건물", body, "buildings.html"))


def building_page(b, units):
    facts = [
        ("크기", "%d칸 (%d블록)" % (b["tiles"], b["blocks"])),
        ("체력", str(b["maxHp"])),
        ("건설 비용", cost(b["cost"])),
        ("공사량", str(b["buildWork"])),
    ]
    if b["workerSlots"]:
        facts.append(("인부 자리", "%d명" % b["workerSlots"]))
    if b["produces"]:
        kind = {"ORE": "광물", "FOOD": "식량", "WOOD": "목재"}.get(b["produces"], b["produces"])
        facts.append(("생산", "%s · 인부 1명당 %s" % (kind, b["perWorker"])))
    if b["housing"]:
        facts.append(("인구 수용", "%d명" % b["housing"]))
    if b["homeland"]:
        facts.append(("필요 지형", b["homeland"]))
    if b["garrisonSlots"]:
        facts.append(("주둔", "%d명" % b["garrisonSlots"]))
    if b["ownRange"]:
        facts.append(("자체 사거리", str(b["ownRange"])))
    elif b["rangeBonus"] != 1:
        facts.append(("사거리 배율", "x%s" % b["rangeBonus"]))
    ft = "".join("<tr><th>%s</th><td>%s</td></tr>" % (e(a), v) for a, v in facts)

    up = ""
    if b["upgradeCosts"]:
        up = "<tr><th>Lv1</th><td class='muted'>건설 시점</td></tr>"
        for u in b["upgradeCosts"]:
            extra = ""
            if b["garrisonSlots"]:
                extra = " <span class='muted'>· 주둔 %d명</span>" % u["garrisonSlots"]
            up += "<tr><th>Lv%d</th><td>%s%s</td></tr>" % (u["to"], cost(u["cost"]), extra)
        up = ("<section><h2>강화</h2><table class='facts'><tbody>%s</tbody></table>"
              "<p class='muted small'>연구소를 지을 수 없는 종족은 연구 없이 Lv4까지 갑니다.</p>"
              "</section>" % up)

    tr = ""
    if b["trains"]:
        tr = ("<section><h2>여기서 나오는 병종</h2><div class='chips'>%s</div></section>"
              % "".join('<a class="chip" href="../unit/%s.html">%s <span class="muted">T%d</span></a>'
                        % (i, e(units[i]["korean"]), units[i]["tier"]) for i in b["trains"]))

    tags = '<span class="tag">%s</span><span class="tag">%s</span>' % (
        e(b["scale"]), e(b["wing"]))
    if not b["placeable"]:
        tags += '<span class="tag off">건설 메뉴에 없음</span>'

    body = """
<p class="crumb"><a href="../buildings.html">건물</a> / %s</p>
<h1>%s</h1>
<p class="lead">%s</p>
<p class="tags">%s</p>
<p class="pills">%s</p>
<section><h2>제원</h2><table class="facts"><tbody>%s</tbody></table></section>
%s
%s
""" % (e(b["korean"]), e(b["korean"]), e(b["purpose"]), tags,
       race_pills(b["raisableBy"], "../"), ft, up, tr)
    write("building/%s.html" % b["id"], page(1, b["korean"], body, "buildings.html"))


# ---------------------------------------------------------------- units
def listing_units(doc):
    rows = ""
    shown = [u for u in doc["units"] if u["recruitable"] or u["undead"] or u["militia"]]
    for u in sorted(shown, key=lambda x: (x["tier"], x["role"], x["korean"])):
        rows += """
    <tr data-races="%s" data-name="%s">
      <td class="num">T%d</td>
      <td><a href="unit/%s.html">%s</a></td>
      <td>%s</td>
      <td class="num">%d</td>
      <td class="num">%d</td>
      <td class="num">%s</td>
      <td>%s</td>
      <td class="pills">%s</td>
    </tr>""" % (" ".join(u["fieldableBy"]), e(u["korean"]), u["tier"], u["id"],
                e(u["korean"]), e(u["role"]), u["maxHp"], u["damage"], u["range"],
                cost(u["cost"]), race_pills(u["fieldableBy"], ""))
    body = """
<h1>병종 <span class="muted">%d</span></h1>
<p class="sub">티어는 무기고 계열 레벨로 열립니다 — T2는 Lv1, T5는 Lv4가 필요합니다.
   소환되거나 탈것에 딸려오는 병종은 목록에서 뺐습니다.</p>
%s
<table class="list" id="tbl">
<thead><tr><th class="num">T</th><th>이름</th><th>역할</th><th class="num">체력</th>
<th class="num">공격</th><th class="num">사거리</th><th>비용</th><th>종족</th></tr></thead>
<tbody>%s</tbody></table>
%s
""" % (len(shown), FILTER, rows, FILTER_JS)
    write("units.html", page(0, "병종", body, "units.html"))


def unit_page(u, builds):
    facts = [
        ("역할", "%s · T%d" % (u["role"], u["tier"])),
        ("체력", str(u["maxHp"])),
        ("공격력", str(u["damage"])),
        ("사거리", str(u["range"])),
        ("이동", "%s 블록/초" % u["blocksPerSecond"]),
        ("비용", cost(u["cost"])),
        ("유지비", str(u["upkeep"])),
        ("훈련 건물", '<a href="../building/%s.html">%s</a>'
         % (u["trainedAt"], e(builds[u["trainedAt"]]["korean"]))),
    ]
    if u["residents"] != 1:
        facts.append(("차지 인구", "%d명" % u["residents"]))
    if u["homeland"]:
        facts.append(("필요 지형", u["homeland"]))
    if u["coastal"]:
        facts.append(("필요 지형", "해안"))
    ft = "".join("<tr><th>%s</th><td>%s</td></tr>" % (e(a), v) for a, v in facts)

    tags = []
    for key, label in [("ranged", "원거리"), ("hybrid", "근접 겸용"), ("mounted", "기승"),
                       ("medic", "치유"), ("hired", "용병"), ("undead", "소생체"),
                       ("militia", "민병"), ("mindless", "야수"), ("golem", "골렘"),
                       ("summoned", "소환"), ("crewOnly", "승무원")]:
        if u.get(key):
            tags.append('<span class="tag">%s</span>' % label)
    if not u["labours"]:
        tags.append('<span class="tag off">노동 불가</span>')

    def bullets(items, cls):
        if not items:
            return ""
        return "<ul class='%s'>%s</ul>" % (cls, "".join("<li>%s</li>" % e(i) for i in items))

    match = ""
    if u["strongAgainst"] or u["weakAgainst"]:
        match = """
<section><h2>상성</h2><div class="grid2">
  <div><h3 class="good">강함</h3>%s</div>
  <div><h3 class="bad">약함</h3>%s</div>
</div></section>""" % (bullets(u["strongAgainst"], "good") or "<p class='muted'>-</p>",
                       bullets(u["weakAgainst"], "bad") or "<p class='muted'>-</p>")

    lim = ""
    if u["limits"]:
        lim = "<section><h2>조건과 제약</h2>%s</section>" % bullets(u["limits"], "bad")

    body = """
<p class="crumb"><a href="../units.html">병종</a> / %s</p>
<h1>%s <span class="muted">T%d</span></h1>
<p class="pills">%s</p>
<p class="tags">%s</p>
<section><h2>제원</h2><table class="facts"><tbody>%s</tbody></table></section>
%s
%s
""" % (e(u["korean"]), e(u["korean"]), u["tier"], race_pills(u["fieldableBy"], "../"),
       "".join(tags), ft, lim, match)
    write("unit/%s.html" % u["id"], page(1, u["korean"], body, "units.html"))


# ---------------------------------------------------------------- research
def research(doc):
    ar = ""
    for r in doc["armouryResearch"]:
        lv = " · ".join("Lv%d %s" % (c["to"], strip(cost(c["cost"]))) for c in r["costs"])
        ar += "<tr><td><b>%s</b></td><td>%s</td><td class='muted small'>%s</td></tr>" % (
            e(r["korean"]), e(r["effect"]), lv)

    tracks = {}
    for l in doc["labs"]:
        tracks.setdefault((l["track"], l["trackNote"]), []).append(l)
    lab = ""
    for (t, note), items in tracks.items():
        rows = "".join(
            "<tr><td><b>%s</b></td><td>%s</td><td>%s</td></tr>"
            % (e(i["korean"]), e(i["effect"]), cost(i["cost"])) for i in items)
        lab += ("<h3>%s <span class='muted'>%s</span></h3>"
                "<table class='cmds'><tbody>%s</tbody></table>" % (e(t), e(note), rows))

    doc_ = ""
    for d in doc["doctrines"]:
        hit = ", ".join(d["affects"][:8]) + (" 외 %d" % (len(d["affects"]) - 8)
                                             if len(d["affects"]) > 8 else "")
        doc_ += ("<tr><td><b>%s</b></td><td>%s</td><td class='muted small'>%s</td>"
                 "<td>%s</td></tr>" % (e(d["korean"]), e(d["effect"]), e(hit), cost(d["cost"])))

    body = """
<h1>연구</h1>
<p class="sub">세 갈래가 서로 다른 건물에 붙어 있고, 하는 일도 다릅니다.</p>

<section>
  <h2>무기고 연구 <span class="muted">전 병종 강화</span></h2>
  <p class="sub">무기고(피글린은 괴수 우리)에서 삽니다. 인부 없이 진행되고,
     건물 레벨이 곧 속도입니다. 각 3단계까지.</p>
  <table class="cmds"><tbody>%s</tbody></table>
</section>

<section>
  <h2>연구소 <span class="muted">갈래마다 하나만</span></h2>
  <p class="sub">이방인 전용 건물입니다. 갈래마다 딱 하나를 고르고, 고르면 바꿀 수 없습니다.
     다른 종족은 연구소를 지을 수 없는 대신, 연구가 걸린 건물 레벨 제한을 받지 않습니다.</p>
  %s
</section>

<section>
  <h2>대학 교리 <span class="muted">병종별 특기</span></h2>
  <p class="sub">한 번 가르치면 늘 참입니다. 장비가 바뀌는 교리는 이미 있는 병사에게도
     소급 적용됩니다.</p>
  <table class="cmds"><tbody>%s</tbody></table>
</section>
""" % (ar, lab, doc_)
    write("research.html", page(0, "연구", body, "research.html"))


def strip(s):
    import re
    return re.sub(r"<[^>]+>", "", s)


# ---------------------------------------------------------------- chrome
FILTER = """
<div class="filter">
  <input id="q" type="search" placeholder="이름으로 거르기…" autocomplete="off">
  <span class="races">
    <button class="pill on" data-race="">전체</button>
    <button class="pill out" data-race="OUTLANDER">이방인</button>
    <button class="pill vil" data-race="VILLAGER">주민</button>
    <button class="pill und" data-race="UNDEAD">언데드</button>
    <button class="pill pig" data-race="PIGLIN">피글린</button>
  </span>
</div>"""

FILTER_JS = """
<script>
(function () {
  var q = document.getElementById('q');
  var rows = [].slice.call(document.querySelectorAll('#tbl tbody tr'));
  var race = '';
  function apply() {
    var t = q.value.trim();
    rows.forEach(function (r) {
      var okName = !t || r.dataset.name.indexOf(t) !== -1;
      var okRace = !race || r.dataset.races.split(' ').indexOf(race) !== -1;
      r.hidden = !(okName && okRace);
    });
  }
  q.addEventListener('input', apply);
  [].slice.call(document.querySelectorAll('.races .pill')).forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('.races .pill').forEach(function (x) {
        x.classList.remove('on');
      });
      b.classList.add('on');
      race = b.dataset.race;
      apply();
    });
  });
})();
</script>"""

CSS = """/* Generated site for 마인토피아 TerritoryWar. */
:root {
  --bg: #0f1115; --panel: #161a21; --line: #262c36;
  --ink: #e6e9ef; --dim: #97a0b0; --faint: #6b7484;
  --gold: #d9a441; --good: #6dbf73; --bad: #d9736b;
  --out: #6f9ad9; --vil: #6dbf73; --und: #9b7fd4; --pig: #d97f6d;
  --ore: #9aa7bd; --food: #cf9f5a; --wood: #a3805a;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.7 "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
}
a { color: inherit; text-decoration: none; }
main a:not(.chip):not(.pill):not(.card):not(.btn) {
  color: var(--gold); border-bottom: 1px solid rgba(217,164,65,.3);
}
main a:not(.chip):not(.pill):not(.card):not(.btn):hover { border-bottom-color: var(--gold); }

header {
  position: sticky; top: 0; z-index: 5; display: flex; flex-wrap: wrap; gap: 16px;
  align-items: center; padding: 14px 24px; background: rgba(15,17,21,.92);
  border-bottom: 1px solid var(--line); backdrop-filter: blur(8px);
}
.brand { font-size: 15px; color: var(--dim); letter-spacing: .02em; }
.brand b { color: var(--ink); }
header nav { display: flex; gap: 4px; margin-left: auto; flex-wrap: wrap; }
header nav a {
  padding: 6px 12px; border-radius: 7px; color: var(--dim); font-size: 14px;
}
header nav a:hover { background: var(--panel); color: var(--ink); }
header nav a.on { background: var(--panel); color: var(--gold); }

main { max-width: 1000px; margin: 0 auto; padding: 40px 24px 80px; }
footer {
  max-width: 1000px; margin: 0 auto; padding: 24px; color: var(--faint);
  font-size: 13px; border-top: 1px solid var(--line);
}

h1 { font-size: 30px; margin: 0 0 8px; letter-spacing: -.01em; }
h2 { font-size: 19px; margin: 0 0 10px; }
h3 { font-size: 15px; margin: 18px 0 8px; }
section { margin: 34px 0; }
p { margin: 0 0 12px; }
.lead { font-size: 17px; color: var(--dim); max-width: 70ch; }
.sub { color: var(--dim); font-size: 14px; max-width: 74ch; }
.muted { color: var(--faint); font-weight: 400; }
.small { font-size: 13px; }
.crumb { color: var(--faint); font-size: 13px; margin-bottom: 6px; }
.good { color: var(--good); } .bad { color: var(--bad); }

.hero { padding: 20px 0 8px; }
.hero h1 { font-size: 42px; }
.cta { display: flex; gap: 10px; margin-top: 18px; flex-wrap: wrap; }
.btn {
  padding: 10px 18px; border-radius: 9px; background: var(--gold); color: #1a1408;
  font-weight: 600; font-size: 14px;
}
.btn.ghost { background: transparent; color: var(--ink); border: 1px solid var(--line); }

.cards { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
.card {
  display: block; padding: 18px; border-radius: 12px; background: var(--panel);
  border: 1px solid var(--line); border-top: 2px solid var(--line);
}
.card:hover { border-color: #39414f; }
.card h3 { margin: 0 0 8px; font-size: 17px; }
.card p { color: var(--dim); font-size: 13.5px; margin: 0; }
.card .stat { display: flex; gap: 12px; margin-top: 12px; color: var(--faint); font-size: 12.5px; }
.card.out { border-top-color: var(--out); } .card.out h3 { color: var(--out); }
.card.vil { border-top-color: var(--vil); } .card.vil h3 { color: var(--vil); }
.card.und { border-top-color: var(--und); } .card.und h3 { color: var(--und); }
.card.pig { border-top-color: var(--pig); } .card.pig h3 { color: var(--pig); }
h1.out { color: var(--out); } h1.vil { color: var(--vil); }
h1.und { color: var(--und); } h1.pig { color: var(--pig); }

.flow { margin: 0; padding-left: 20px; color: var(--dim); }
.flow li { margin-bottom: 8px; }
.flow b { color: var(--ink); }
ul.plain { margin: 0; padding-left: 18px; color: var(--dim); }
ul.plain li { margin-bottom: 6px; }
ul.good, ul.bad { margin: 0; padding-left: 18px; }
ul.good li { color: var(--good); } ul.bad li { color: var(--bad); }
.grid2 { display: grid; gap: 24px; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }

table { width: 100%; border-collapse: collapse; font-size: 14px; }
.list, .cmds, .keys, .facts { background: var(--panel); border-radius: 10px; overflow: hidden; }
th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--line); }
thead th { color: var(--faint); font-weight: 500; font-size: 12.5px; }
tbody tr:last-child td, tbody tr:last-child th { border-bottom: 0; }
tbody tr:hover { background: rgba(255,255,255,.02); }
.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.facts th { color: var(--faint); font-weight: 500; width: 130px; }
.keys td:first-child { width: 54px; }
.cmds td:first-child { white-space: nowrap; width: 1%; }
.list a { font-weight: 600; }
.wrap { overflow-x: auto; }

kbd {
  display: inline-block; min-width: 22px; text-align: center; padding: 2px 7px;
  border-radius: 5px; background: #212734; border: 1px solid var(--line);
  border-bottom-width: 2px; font: 600 12.5px/1.5 ui-monospace, monospace; color: var(--ink);
}
code {
  font: 13px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace;
  background: #1b2029; padding: 2px 6px; border-radius: 5px; color: #cbd3e1;
}

.pill {
  display: inline-block; padding: 2px 9px; margin: 0 4px 4px 0; border-radius: 20px;
  font-size: 12px; background: #1e242e; color: var(--dim); border: 1px solid transparent;
  cursor: pointer; font-family: inherit;
}
.pill.out { color: var(--out); } .pill.vil { color: var(--vil); }
.pill.und { color: var(--und); } .pill.pig { color: var(--pig); }
.pill.on { background: var(--gold); color: #1a1408; }
.pills { line-height: 2.1; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  padding: 5px 11px; border-radius: 8px; background: var(--panel);
  border: 1px solid var(--line); font-size: 13.5px;
}
.chip:hover { border-color: #39414f; }
.tier { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.tier .t { color: var(--faint); font-size: 12px; width: 26px; }
.tags { line-height: 2.2; }
.tag {
  display: inline-block; padding: 2px 9px; margin-right: 5px; border-radius: 6px;
  background: #1e242e; color: var(--dim); font-size: 12px;
}
.tag.off { color: var(--bad); }

.r { font-size: 12.5px; white-space: nowrap; }
.r.ore { color: var(--ore); } .r.food { color: var(--food); } .r.wood { color: var(--wood); }

.filter { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; margin: 18px 0 12px; }
#q {
  flex: 1 1 200px; padding: 9px 13px; border-radius: 9px; background: var(--panel);
  border: 1px solid var(--line); color: var(--ink); font: inherit; font-size: 14px;
}
#q:focus { outline: none; border-color: #39414f; }

@media (max-width: 640px) {
  main { padding: 24px 16px 60px; }
  .hero h1 { font-size: 32px; }
  header { padding: 12px 16px; }
  table { font-size: 13px; }
  th, td { padding: 7px 8px; }
}
"""

if __name__ == "__main__":
    build()
