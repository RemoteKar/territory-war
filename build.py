# -*- coding: utf-8 -*-
"""Builds the reference site out of the game's own dump.

Nothing here knows a rule. Every number, name and sentence on the finished pages comes
from data/docs.json, which the plugin writes with `tw docs` on the console - so a balance
change is one dump and one run away from being on the site, and there is no second copy of
the rules to drift out of step with the first.

The hand-written prose is checked against the humanize-korean taxonomy
(github.com/epoko77-ai/im-not-ai) before it ships. Two of its measures drove the rewrite:
connective endings followed by a comma (C-11, the strongest single tell in the whole
scheme, and this site scored 60% against a human baseline of 4%) and sentence-ending
uniformity (E-2). Run tools/diagnose.py after touching any of the copy below.

    python build.py            # -> docs/
"""
import html
import json
import io
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "docs")
DATA = os.path.join(HERE, "data", "docs.json")

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


def page(depth, title, body, active, wide=False):
    """One HTML file. `depth` is how many directories deep it sits."""
    up = "../" * depth
    nav = "".join(
        '<a href="%s%s"%s>%s</a>' % (up, href, ' class="on"' if href == active else "", label)
        for href, label in NAV
    )
    return """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>%s · 마인토피아 TerritoryWar</title>
<link rel="stylesheet" href="%sassets/style.css">
</head>
<body>
<header class="bar">
  <a class="brand" href="%sindex.html"><span>마인토피아</span> TerritoryWar</a>
  <nav>%s</nav>
</header>
<main%s>
%s
</main>
<footer>
  <span>마인크래프트 위의 타일 전략</span>
  <span>표와 수치는 게임 데이터에서 그대로 뽑아 씁니다</span>
</footer>
</body>
</html>
""" % (e(title), up, up, nav, ' class="wide"' if wide else "", body)


def cost(c):
    bits = []
    if c["ore"]:
        bits.append('<i class="ore">광물 %d</i>' % c["ore"])
    if c["food"]:
        bits.append('<i class="food">식량 %d</i>' % c["food"])
    if c["wood"]:
        bits.append('<i class="wood">목재 %d</i>' % c["wood"])
    return '<span class="r">%s</span>' % "".join(bits) if bits else '<span class="muted">무료</span>'


def plain(s):
    return re.sub(r"<[^>]+>", "", s)


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
    builds = {b["id"]: b for b in doc["buildings"]}
    units = {u["id"]: u for u in doc["units"]}

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for d in ["", "race", "building", "unit", "assets"]:
        os.makedirs(os.path.join(OUT, d), exist_ok=True)

    write("assets/style.css", CSS)
    write(".nojekyll", "")
    shutil.copy(DATA, os.path.join(OUT, "docs.json"))

    index(doc)
    controls()
    race_index(doc)
    for r in doc["races"]:
        race_page(r, builds, units)
    listing_buildings(doc)
    for b in doc["buildings"]:
        building_page(b, units)
    listing_units(doc)
    for u in doc["units"]:
        unit_page(u, builds)
    research(doc)

    n = sum(len(f) for _, _, f in os.walk(OUT))
    print("built %d files into %s" % (n, OUT))


def write(rel, content):
    p = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(content)


# ---------------------------------------------------------------- index
def index(doc):
    cards = ""
    for r in doc["races"]:
        cards += """
    <a class="race-card %s" href="race/%s.html">
      <span class="rule"></span>
      <h3>%s</h3>
      <p>%s</p>
      <div class="meta"><span>건물 %d</span><span>병종 %d</span></div>
    </a>""" % (RACE_TAG[r["id"]], r["id"], e(r["korean"]), e(r["blurb"]),
               len(r["buildings"]), len(r["units"]))

    flow = [
        ("정착", "필드맵에서 칸을 점유하고 타운홀을 세운다."),
        ("경제", "인구가 곧 인부. 인력 배분에서 건설과 생산의 비율을 정하면 나머지는 알아서 굴러간다."),
        ("확장", "집을 올려 인구 한도를 밀어올린다. 생산 건물은 레벨이 곧 산출량."),
        ("군비", "무기고 계열 레벨이 병종 티어를 연다. 연구가 올려주는 건 능력치뿐."),
        ("원정", "출진 창에서 병력과 보급을 싣는다. 보급이 떨어진 원정대는 굶는다."),
        ("결착", "상대의 타운홀을 부수거나 외교로 항복을 받아낸다."),
    ]
    steps = "".join('<li><b>%s</b><span>%s</span></li>' % (a, b) for a, b in flow)

    counts = [("종족", len(doc["races"])),
              ("건물", len(doc["buildings"])),
              ("병종", len(doc["units"])),
              ("연구", len(doc["armouryResearch"]) + len(doc["labs"]) + len(doc["doctrines"]))]
    strip = "".join('<div><b>%d</b><span>%s</span></div>' % (v, k) for k, v in counts)

    body = """
<section class="hero">
  <p class="kicker">마인크래프트 위의 타일 전략</p>
  <h1>영토 전쟁</h1>
  <p class="lead">
    땅을 점유해 정착지를 올리고 인구를 노동과 병력으로 갈라 쓴다.
    원정대를 꾸려 이웃의 국경을 넘는 데까지가 한 판.
    타운홀이 무너진 나라는 그 자리에서 사라진다.
  </p>
  <div class="cta">
    <a class="btn" href="controls.html">조작부터 보기</a>
    <a class="btn ghost" href="races.html">종족 고르기</a>
  </div>
  <div class="strip">%s</div>
</section>

<section>
  <h2>네 개의 종족</h2>
  <p class="sub">같은 지도를 서로 다른 방식으로 산다.
     무엇을 고르느냐에 따라 지을 건물과 뽑을 병종이 통째로 갈린다.</p>
  <div class="race-grid">%s</div>
</section>

<section>
  <h2>한 판의 흐름</h2>
  <ol class="steps">%s</ol>
</section>

<section class="split">
  <div>
    <h2>판을 읽는 법</h2>
    <p>인구는 곧 노동이자 병력. 한 명을 징집하면 생산에서 그만큼 빠지니
       군대를 불릴수록 경제는 얇아진다.</p>
    <p>상성이 전투를 가른다. 창병은 기병에게 강하고 경보병에게 약하다.
       지형 특산 병종과 건물은 그 지형을 점유해야 열리는 것들.</p>
    <p>장벽은 길을 막는 판정일 뿐. 실제 블록으로 이어지지 않으니
       전투가 붙은 칸에 새로 세우지 못한다.</p>
  </div>
  <div>
    <h2>이 문서에 대하여</h2>
    <p>이 표들은 어디서 왔나. 서버 콘솔에서 <code>tw docs</code> 를 치면 플러그인이
       자기 데이터를 그대로 뱉고, 이 페이지들은 그것만 읽어 만들어진다.
       밸런스를 고치면 문서도 같이 따라온다.</p>
    <p class="links">
      <a href="docs.json">docs.json 내려받기</a>
      <a href="https://github.com/RemoteKar/territory-war">GitHub</a>
    </p>
    <p class="muted small">데이터 생성 %s</p>
  </div>
</section>
""" % (strip, cards, steps, e(doc["generated"][:10]))
    write("index.html", page(0, "소개", body, "index.html"))


# ---------------------------------------------------------------- controls
def controls():
    """The command tables were checked one by one against TwCommand's dispatcher.

    They were first lifted out of the in-game help text, which turned out to be a
    different list: the help page has never mentioned `/tw preset`, and starting a nation
    does not work without it.
    """
    def row(k, name, note):
        return "<tr><td><kbd>%s</kbd></td><th>%s</th><td>%s</td></tr>" % (k, name, note)

    def clist(rows):
        return "".join("<tr><td><code>%s</code></td><td>%s</td></tr>" % (c, d)
                       for c, d in rows)

    starting = [
        ("/tw preset", "국가 이름·색·문양·<b>종족</b>을 고른다. 한 번이면 된다"),
        ("/tw join", "참전. <code>/tw play</code> · <code>/tw 참가</code> 로도 된다"),
        ("우클릭", "정착지 선정 단계에 땅을 우클릭해 자리를 잡는다"),
        ("/tw watch", "관전으로 빠진다. 참전 중에는 바꾸지 못한다"),
        ("/tw phase", "현재 단계와 남은 시간"),
    ]
    idle = "".join([
        row("1", "필드맵 · 정착지", "영토와 요새, 나가 있는 원정대를 본다"),
        row("2", "건물 건설", "고른 뒤 지을 곳을 조준한다"),
        row("3", "외교", "동맹 · 항복 · 지원"),
        row("4", "출진", "병력과 보급을 실어 내보낸다"),
        row("5", "국가 정보", "자원과 인구, 정책과 기술을 한 창에서"),
        row("6", "인력 배분", "건설로 나가는 인력. 나머지는 생산 건물로 간다"),
        row("8", "다른 정착지", "내 정착지 사이를 오간다"),
    ])
    sel = "".join([
        row("1", "강화 · 취소", "레벨을 올린다. 진행 중이면 취소하고 자원을 전액 돌려받는다"),
        row("2", "전용 창", "건물마다 다르다. 병종 생산, 연구, 주둔, 민병 무장"),
        row("3", "보조 창", "괴수 우리의 연구, 망루의 주둔 해제"),
        row("4", "상세 정보", "능력치와 상성"),
        row("5", "인부 우선순위", "생산 건물에 사람을 먼저 보낼 순서"),
    ])
    field = "".join([
        row("1", "정착지로", "필드맵에서 돌아온다"),
        row("2", "원정대 목록", "짐과 굶주림까지 나온다"),
        row("3", "보급 · 교역", "정착지에서 물자를 싣고 내린다"),
        row("4", "귀환 · 해산", ""),
        row("6", "필드 건설", "전초기지나 보급기지 같은 야전 건물"),
    ])

    cmds = [
        ("/tw info", "내 나라 요약"),
        ("/tw here", "서 있는 칸 정보"),
        ("/tw list", "나라 목록"),
        ("/tw build [건물]", "인수 없이 치면 건설 창이 열린다"),
        ("/tw claim · unclaim", "칸 점유와 해제"),
        ("/tw upgrade", "서 있는 건물 강화"),
        ("/tw train [병종] [수]", "인수 없이 치면 내 종족의 병종표"),
        ("/tw garrison [병종]", "서 있는 망루나 발리스타에 주둔"),
        ("/tw sortie", "출진 창. 병종과 보급을 슬라이더로 싣는다"),
        ("/tw armies", "원정대 목록. 짐과 굶주림 포함"),
        ("/tw follow", "선택한 원정대 위치로 이동"),
        ("/tw recallarmy", "선택한 원정대 정지"),
        ("/tw trade", "선택한 원정대로 정착지에서 거래"),
        ("/tw pack [reload]", "리소스팩 상태와 재전송"),
        ("/tw 설정", "라운드 규칙 보기와 변경"),
    ]
    war = [
        ("/tw siege &lt;국가&gt;", "상대 타운홀 쪽으로 바위를 던진다. 광물 15. "
                              "물리 탄도라 튕기고 굴러서 <b>멈춘 칸의 건물</b>이 맞는다"),
        ("/tw diplomacy", "외교 창. 동맹과 항복, 지원"),
        ("/tw ally &lt;국가&gt;", "동맹 제안. 이미 동맹이면 파기"),
        ("/tw surrender &lt;국가&gt;", "항복 제안. 비축 절반을 배상하고 속국이 된다"),
        ("/tw accept &lt;국가&gt;", "받은 제안 수락"),
        ("/tw offers", "받은 제안 목록"),
        ("/tw gift &lt;국가&gt; &lt;자원&gt; &lt;수량&gt;", "자원 지원"),
        ("/tw 비난 &lt;국가&gt;", "공개 규탄. 실질 효과는 없다"),
    ]
    admin = [
        ("/tw start [초]", "정착지 선정 시작"),
        ("/tw 치트 시작 [국가명]", "대기와 선정을 건너뛰고 즉시 정착지 생성"),
        ("/tw 치트 자원 [양]", "광물·식량·목재를 그만큼. 기본 1000"),
        ("/tw 치트 완공", "건설과 강화 즉시 완료"),
        ("/tw 치트 유닛 &lt;병종&gt; [수]", "즉시 생성. 비용과 훈련을 무시한다"),
        ("/tw 치트 적 &lt;병종&gt; [수]", "적대 AI 병사 생성"),
        ("/tw 치트 적정리", "생성한 적을 전부 지운다"),
        ("/tw 치트 전투 [규모]", "모의전. 검병:궁수:창기병 = 60:20:10"),
        ("/tw 치트 배속 [배]", "경제 속도"),
        ("/tw 설정 인구 &lt;최대&gt;", "0 이면 무제한"),
        ("/tw 설정 정예 &lt;수&gt;", "5티어 병종 동시 보유 상한"),
        ("/tw 설정 리로드", "config.yml 을 재시작 없이 다시 읽는다"),
        ("/tw 래그돌 [무손상|팔|덩어리|산산조각]", "바라보는 곳에 시체 하나"),
        ("/tw 샌드박스", "모델 전시장"),
        ("/tw 트림", "갑옷 트림 목록"),
        ("/tw 스킨목록 · /tw 스킨 &lt;이름&gt;", "마네킹 스킨 목록과 미리보기"),
        ("tw docs", "콘솔 전용. 이 문서의 원본 데이터를 쓴다"),
    ]

    body = """
<header class="page-head">
  <p class="kicker">조작</p>
  <h1>손에 익히는 순서</h1>
  <p class="lead">조작은 거의 다 핫바에서 끝난다.
     무엇을 선택했느냐에 따라 같은 숫자 키가 다른 일을 한다.</p>
</header>

<section>
  <h2>시작하기</h2>
  <p class="sub">순서는 이렇다. <code>/tw nation</code> 은 폐지됐고
     건국은 <b>preset 한 번에 join</b>.</p>
  <table class="cmds"><tbody>%s</tbody></table>
</section>

<section class="split">
  <div>
    <h2>선택한 것이 없을 때</h2>
    <table class="keys"><tbody>%s</tbody></table>
  </div>
  <div>
    <h2>필드맵에서</h2>
    <table class="keys"><tbody>%s</tbody></table>
  </div>
</section>

<section>
  <h2>건물을 선택했을 때</h2>
  <p class="sub">건물을 바라보고 좌클릭하면 잡힌다.</p>
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
""" % (clist(starting), idle, field, sel, clist(cmds), clist(war), clist(admin))
    write("controls.html", page(0, "조작", body, "controls.html"))


# ---------------------------------------------------------------- races
def race_index(doc):
    cards = ""
    for r in doc["races"]:
        cards += """
    <a class="race-card big %s" href="race/%s.html">
      <span class="rule"></span>
      <h3>%s</h3>
      <p>%s</p>
      <div class="meta"><span>건물 %d</span><span>병종 %d</span><span>정책 %d</span></div>
    </a>""" % (RACE_TAG[r["id"]], r["id"], e(r["korean"]), e(r["blurb"]),
               len(r["buildings"]), len(r["units"]), len(r["policies"]))
    body = """
<header class="page-head">
  <p class="kicker">종족</p>
  <h1>같은 지도, 다른 살림</h1>
  <p class="lead">고르는 순간 지을 건물과 뽑을 병종이 갈린다.
     경제도 제각각. 밭을 가는 쪽이 있고 포로를 잡아오는 쪽이 있다.</p>
</header>
<div class="race-grid">%s</div>
""" % cards
    write("races.html", page(0, "종족", body, "races.html"))


def race_page(r, builds, units):
    rid = r["id"]
    facts = [
        ("무기고 계열", builds[r["armoury"]]["korean"], "병종 티어를 여는 건물"),
        ("주거 계열", builds[r["quarters"]]["korean"], "인구 한도를 올리는 건물"),
        ("연구소", "가능" if r["researches"] else "불가",
         "연구소를 못 짓는 종족은 연구 없이 모든 건물이 Lv4까지 간다"),
        ("민간인", "있음" if r["keepsCivilians"] else "없음",
         "민간인이 없으면 징집 대신 값을 치러 병력을 얻는다"),
        ("자연 증가", "있음" if r["growsOnItsOwn"] else "없음", ""),
        ("시체 수급", "있음" if r["reapsRemains"] else "없음", ""),
        ("식량 소모", "x%s" % r["ration"], "병사 한 명당 배급 배율"),
    ]
    ft = "".join("<tr><th>%s</th><td><b>%s</b></td><td class='muted'>%s</td></tr>"
                 % (e(a), e(b), e(c)) for a, b, c in facts)

    chips = "".join(
        '<a class="chip" href="../building/%s.html">%s</a>' % (i, e(builds[i]["korean"]))
        for i in r["buildings"])

    ulist = ""
    for tier in range(1, 6):
        row = [i for i in r["units"] if units[i]["tier"] == tier]
        if not row:
            continue
        ulist += '<div class="tier-row"><span class="t">T%d</span><div>%s</div></div>' % (
            tier, "".join('<a class="chip" href="../unit/%s.html">%s</a>'
                          % (i, e(units[i]["korean"])) for i in row))

    pol = ""
    for p in r["policies"]:
        pol += "<tr><td class='muted'>%s</td><th>%s</th><td>%s</td></tr>" % (
            e(p["group"]), e(p["korean"]), e(p["effect"]))

    body = """
<p class="crumb"><a href="../races.html">종족</a><span>%s</span></p>
<header class="page-head %s">
  <h1>%s</h1>
  <p class="lead">%s</p>
</header>

<section><h2>기본기</h2><table class="facts"><tbody>%s</tbody></table></section>

<section><h2>지을 수 있는 건물 <em>%d</em></h2><div class="chips">%s</div></section>

<section><h2>뽑을 수 있는 병종 <em>%d</em></h2>%s</section>

<section><h2>정책 <em>%d</em></h2><table class="cmds"><tbody>%s</tbody></table></section>
""" % (e(r["korean"]), RACE_TAG[rid], e(r["korean"]), e(r["blurb"]), ft,
       len(r["buildings"]), chips,
       len(r["units"]), ulist or '<p class="muted">훈련으로 얻는 병종이 없다.</p>',
       len(r["policies"]), pol or "<tr><td class='muted'>정책을 고르지 않는 종족.</td></tr>")
    write("race/%s.html" % rid, page(1, r["korean"], body, "races.html"))


# ---------------------------------------------------------------- buildings
def listing_buildings(doc):
    # The halls and the round's furniture are not on any build menu, so they are not on
    # this list either - see Docs.placeable. They keep their own pages.
    shown = [b for b in doc["buildings"] if b["placeable"]]
    rows = ""
    for b in sorted(shown, key=lambda x: (x["scale"], x["wing"], x["korean"])):
        rows += """
    <tr data-races="%s" data-name="%s">
      <td><a href="building/%s.html">%s</a></td>
      <td class="muted small">%s</td>
      <td class="note">%s</td>
      <td class="num">%d칸</td>
      <td class="num">%d</td>
      <td>%s</td>
      <td class="pills">%s</td>
    </tr>""" % (" ".join(b["raisableBy"]), e(b["korean"]), b["id"], e(b["korean"]),
                e(b["wing"]), e(b["purpose"]), b["tiles"], b["maxHp"], cost(b["cost"]),
                race_pills(b["raisableBy"]))
    halls = "".join(
        '<a class="chip" href="building/%s.html">%s</a>' % (b["id"], e(b["korean"]))
        for b in doc["buildings"] if b["hall"])
    body = """
<header class="page-head">
  <p class="kicker">건물</p>
  <h1>지을 수 있는 것들 <em>%d</em></h1>
  <p class="lead">칸은 차지하는 타일 수, 체력은 부서지기까지 버티는 내구.
     오른쪽 뱃지는 그 건물을 지을 수 있는 종족.</p>
</header>
%s
<div class="tablewrap">
<table class="list" id="tbl">
<thead><tr><th>이름</th><th>분류</th><th>쓰임</th><th class="num">크기</th><th class="num">체력</th>
<th>건설 비용</th><th>종족</th></tr></thead>
<tbody>%s</tbody></table>
</div>
%s
<section><h2>정착지 중심</h2>
<p class="sub">건설 메뉴에 없는 건물. 정착지와 함께 생기고 무너지면 그 나라가 끝난다.</p>
<div class="chips">%s</div></section>
""" % (len(shown), FILTER, rows, FILTER_JS, halls)
    write("buildings.html", page(0, "건물", body, "buildings.html", wide=True))


def building_page(b, units):
    stats = [("크기", "%d칸" % b["tiles"], "%d블록" % b["blocks"]),
             ("체력", str(b["maxHp"]), ""),
             ("공사량", str(b["buildWork"]), "")]
    if b["workerSlots"]:
        stats.append(("인부 자리", "%d명" % b["workerSlots"], ""))
    if b["produces"]:
        kind = {"ORE": "광물", "FOOD": "식량", "WOOD": "목재"}.get(b["produces"], b["produces"])
        stats.append(("생산", kind, "인부 1명당 %s" % b["perWorker"]))
    if b["housing"]:
        stats.append(("인구 수용", "%d명" % b["housing"], ""))
    if b["garrisonSlots"]:
        stats.append(("주둔", "%d명" % b["garrisonSlots"], ""))
    if b["ownRange"]:
        stats.append(("자체 사거리", str(b["ownRange"]), ""))
    elif b["rangeBonus"] != 1:
        stats.append(("사거리", "x%s" % b["rangeBonus"], "올려둔 병사에게"))
    if b["homeland"]:
        stats.append(("필요 지형", b["homeland"], ""))
    grid = "".join(
        '<div class="stat"><span>%s</span><b>%s</b>%s</div>'
        % (e(a), e(v), "<i>%s</i>" % e(n) if n else "") for a, v, n in stats)

    up = ""
    if b["upgradeCosts"]:
        rows = "<tr><th>Lv1</th><td class='muted'>건설 시점</td></tr>"
        for u in b["upgradeCosts"]:
            extra = ""
            if b["garrisonSlots"]:
                extra = " <span class='muted'>· 주둔 %d명</span>" % u["garrisonSlots"]
            rows += "<tr><th>Lv%d</th><td>%s%s</td></tr>" % (u["to"], cost(u["cost"]), extra)
        up = ("<section><h2>강화</h2><table class='facts'><tbody>%s</tbody></table>"
              "<p class='muted small'>연구소를 지을 수 없는 종족은 연구 없이 Lv4까지 간다.</p>"
              "</section>" % rows)

    tr = ""
    if b["trains"]:
        tr = ("<section><h2>여기서 나오는 병종</h2><div class='chips'>%s</div></section>"
              % "".join('<a class="chip" href="../unit/%s.html">%s<em>T%d</em></a>'
                        % (i, e(units[i]["korean"]), units[i]["tier"]) for i in b["trains"]))

    tags = '<span class="tag">%s</span><span class="tag">%s</span>' % (
        e(b["scale"]), e(b["wing"]))
    if not b["placeable"]:
        tags += '<span class="tag off">건설 메뉴에 없음</span>'

    body = """
<p class="crumb"><a href="../buildings.html">건물</a><span>%s</span></p>
<header class="page-head">
  <h1>%s</h1>
  <p class="lead">%s</p>
  <p class="tags">%s</p>
  <p class="pills">%s</p>
</header>
<section><h2>제원</h2><div class="statgrid">%s</div>
<table class="facts"><tbody><tr><th>건설 비용</th><td>%s</td></tr></tbody></table></section>
%s
%s
""" % (e(b["korean"]), e(b["korean"]), e(b["purpose"]), tags,
       race_pills(b["raisableBy"], "../"), grid, cost(b["cost"]), up, tr)
    write("building/%s.html" % b["id"], page(1, b["korean"], body, "buildings.html"))


# ---------------------------------------------------------------- units
def listing_units(doc):
    shown = [u for u in doc["units"] if u["recruitable"] or u["undead"] or u["militia"]]
    rows = ""
    for u in sorted(shown, key=lambda x: (x["tier"], x["role"], x["korean"])):
        rows += """
    <tr data-races="%s" data-name="%s">
      <td class="num"><span class="tier t%d">T%d</span></td>
      <td><a href="unit/%s.html">%s</a></td>
      <td class="muted small">%s</td>
      <td class="num">%d</td>
      <td class="num">%d</td>
      <td class="num">%s</td>
      <td>%s</td>
      <td class="pills">%s</td>
    </tr>""" % (" ".join(u["fieldableBy"]), e(u["korean"]), u["tier"], u["tier"], u["id"],
                e(u["korean"]), e(u["role"]), u["maxHp"], u["damage"], u["range"],
                cost(u["cost"]), race_pills(u["fieldableBy"]))
    body = """
<header class="page-head">
  <p class="kicker">병종</p>
  <h1>부릴 수 있는 것들 <em>%d</em></h1>
  <p class="lead">티어를 여는 건 무기고 계열 레벨. T2는 Lv1, T5는 Lv4가 있어야 한다.
     소환되거나 탈것에 딸려 오는 병종은 뺐다.</p>
</header>
%s
<div class="tablewrap">
<table class="list" id="tbl">
<thead><tr><th class="num">티어</th><th>이름</th><th>역할</th><th class="num">체력</th>
<th class="num">공격</th><th class="num">사거리</th><th>비용</th><th>종족</th></tr></thead>
<tbody>%s</tbody></table>
</div>
%s
""" % (len(shown), FILTER, rows, FILTER_JS)
    write("units.html", page(0, "병종", body, "units.html", wide=True))


def unit_page(u, builds):
    stats = [("체력", str(u["maxHp"]), ""),
             ("공격력", str(u["damage"]), ""),
             ("사거리", str(u["range"]), ""),
             ("이동", str(u["blocksPerSecond"]), "블록/초"),
             ("유지비", str(u["upkeep"]), "")]
    if u["residents"] != 1:
        stats.append(("차지 인구", "%d명" % u["residents"], ""))
    if u["hireCost"]:
        stats.append(("임금", str(u["hireCost"]), "용병"))
    grid = "".join(
        '<div class="stat"><span>%s</span><b>%s</b>%s</div>'
        % (e(a), e(v), "<i>%s</i>" % e(n) if n else "") for a, v, n in stats)

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
            return '<p class="muted">-</p>'
        return "<ul class='%s'>%s</ul>" % (cls, "".join("<li>%s</li>" % e(i) for i in items))

    # Which of the three trees reach this soldier.
    #
    # The armoury picks by melee/ranged, the laboratory by the weapon in the hand and the
    # university by an explicit roster, so a player looking at one unit had no way to see
    # what was worth studying for it. Computed in Docs.java where each tree's own rule is.
    up = u.get("upgrades") or {}
    blocks = []
    for key, title, where in [
            ("armoury", "무기고 연구", "무기고 · 괴수 우리"),
            ("labs", "연구소", "이방인 전용"),
            ("doctrines", "대학 교리", "대학")]:
        items = up.get(key) or []
        if not items:
            continue
        rows = "".join("<tr><th>%s</th><td>%s</td></tr>" % (e(i["korean"]), e(i["effect"]))
                       for i in items)
        blocks.append("<h3>%s <span class='muted'>%s</span></h3>"
                      "<table class='cmds'><tbody>%s</tbody></table>" % (title, where, rows))
    ups = ""
    if blocks:
        ups = ("<section><h2>적용받는 업그레이드</h2>"
               "<p class='sub'>세 갈래가 서로 다른 기준으로 대상을 고른다. "
               "무기고는 근접·원거리로, 연구소는 손에 든 무기로, 대학은 병종 명단으로 고른다.</p>"
               "%s</section>" % "".join(blocks))

    match = ""
    if u["strongAgainst"] or u["weakAgainst"]:
        match = """
<section><h2>상성</h2><div class="split tight">
  <div><h3 class="good">강하다</h3>%s</div>
  <div><h3 class="bad">약하다</h3>%s</div>
</div></section>""" % (bullets(u["strongAgainst"], "good"), bullets(u["weakAgainst"], "bad"))

    lim = ""
    if u["limits"]:
        lim = "<section><h2>조건과 제약</h2>%s</section>" % bullets(u["limits"], "bad")

    body = """
<p class="crumb"><a href="../units.html">병종</a><span>%s</span></p>
<header class="page-head">
  <h1>%s <span class="tier t%d">T%d</span></h1>
  <p class="lead">%s · <a href="../building/%s.html">%s</a> 에서 나온다</p>
  <p class="tags">%s</p>
  <p class="pills">%s</p>
</header>
<section><h2>제원</h2><div class="statgrid">%s</div>
<table class="facts"><tbody><tr><th>비용</th><td>%s</td></tr></tbody></table></section>
%s
%s
%s
""" % (e(u["korean"]), e(u["korean"]), u["tier"], u["tier"], e(u["role"]),
       u["trainedAt"], e(builds[u["trainedAt"]]["korean"]),
       "".join(tags), race_pills(u["fieldableBy"], "../"), grid, cost(u["cost"]),
       lim, match, ups)
    write("unit/%s.html" % u["id"], page(1, u["korean"], body, "units.html"))


# ---------------------------------------------------------------- research
def research(doc):
    ar = ""
    for r in doc["armouryResearch"]:
        lv = " · ".join("Lv%d %s" % (c["to"], plain(cost(c["cost"]))) for c in r["costs"])
        ar += "<tr><th>%s</th><td>%s</td><td class='muted small'>%s</td></tr>" % (
            e(r["korean"]), e(r["effect"]), lv)

    tracks = {}
    for l in doc["labs"]:
        tracks.setdefault((l["track"], l["trackNote"]), []).append(l)
    lab = ""
    for (t, note), items in tracks.items():
        rows = "".join(
            "<tr><th>%s</th><td>%s</td><td>%s</td></tr>"
            % (e(i["korean"]), e(i["effect"]), cost(i["cost"])) for i in items)
        lab += ("<h3>%s <span class='muted'>%s</span></h3>"
                "<table class='cmds'><tbody>%s</tbody></table>" % (e(t), e(note), rows))

    dc = ""
    for d in doc["doctrines"]:
        hit = ", ".join(d["affects"][:8])
        if len(d["affects"]) > 8:
            hit += " 외 %d" % (len(d["affects"]) - 8)
        dc += ("<tr><th>%s</th><td>%s</td><td class='muted small'>%s</td>"
               "<td>%s</td></tr>" % (e(d["korean"]), e(d["effect"]), e(hit), cost(d["cost"])))

    body = """
<header class="page-head">
  <p class="kicker">연구</p>
  <h1>세 갈래의 기술</h1>
  <p class="lead">서로 다른 건물에 붙어 있고 하는 일도 다르다.
     무기고는 병종을 강하게 만들고 연구소는 갈래마다 하나를 고르게 하며
     대학은 병종별 특기를 가르친다.</p>
</header>

<section>
  <h2>무기고 연구 <span class="muted">전 병종 강화</span></h2>
  <p class="sub">무기고에서 산다. 피글린은 괴수 우리가 그 자리를 대신한다.
     인부 없이 진행되고 건물 레벨이 곧 속도. 각 3단계까지 올라간다.</p>
  <table class="cmds"><tbody>%s</tbody></table>
</section>

<section>
  <h2>연구소 <span class="muted">갈래마다 하나</span></h2>
  <p class="sub">이방인만 짓는 건물. 갈래마다 딱 하나를 고르고 한번 고르면 못 바꾼다.
     다른 종족은 연구소가 없는 대신 연구가 걸린 건물 레벨 제한을 받지 않는다.</p>
  %s
</section>

<section>
  <h2>대학 교리 <span class="muted">병종별 특기</span></h2>
  <p class="sub">한 번 가르치면 늘 참. 장비가 바뀌는 교리는 이미 세워둔 병사에게도
     소급 적용된다.</p>
  <table class="cmds"><tbody>%s</tbody></table>
</section>
""" % (ar, lab, dc)
    write("research.html", page(0, "연구", body, "research.html"))


# ---------------------------------------------------------------- chrome
FILTER = """
<div class="filter">
  <input id="q" type="search" placeholder="이름으로 거르기" autocomplete="off">
  <div class="races">
    <button class="pill on" data-race="">전체</button>
    <button class="pill out" data-race="OUTLANDER">이방인</button>
    <button class="pill vil" data-race="VILLAGER">주민</button>
    <button class="pill und" data-race="UNDEAD">언데드</button>
    <button class="pill pig" data-race="PIGLIN">피글린</button>
  </div>
  <span class="count" id="count"></span>
</div>"""

FILTER_JS = """
<script>
(function () {
  var q = document.getElementById('q');
  var out = document.getElementById('count');
  var rows = [].slice.call(document.querySelectorAll('#tbl tbody tr'));
  var race = '';
  function apply() {
    var t = q.value.trim(), n = 0;
    rows.forEach(function (r) {
      var ok = (!t || r.dataset.name.indexOf(t) !== -1)
            && (!race || r.dataset.races.split(' ').indexOf(race) !== -1);
      r.hidden = !ok;
      if (ok) n++;
    });
    out.textContent = n + ' / ' + rows.length;
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
  apply();
})();
</script>"""

CSS = """/* Generated site for 마인토피아 TerritoryWar. */
:root {
  --bg:#0b0d11; --bg2:#0f1218; --panel:#141922; --panel2:#182029;
  --line:#222a36; --line2:#2c3644;
  --ink:#e8ecf3; --dim:#9aa5b6; --faint:#69748a;
  --gold:#e0b055; --good:#74c78a; --bad:#e08278;
  --out:#79a6e8; --vil:#74c78a; --und:#a98fe0; --pig:#e08a72;
  --ore:#a8b4c8; --food:#d9a862; --wood:#b08a62;
  --r:12px;
}
* { box-sizing:border-box; }
html { -webkit-text-size-adjust:100%; }
body {
  margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.75 "Pretendard","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;
}
a { color:inherit; text-decoration:none; }

/* ---------------------------------------------------------------- chrome */
.bar {
  position:sticky; top:0; z-index:20; display:flex; gap:20px; align-items:center;
  flex-wrap:wrap; padding:0 28px; min-height:60px;
  background:rgba(11,13,17,.86); backdrop-filter:blur(14px) saturate(1.4);
  border-bottom:1px solid var(--line);
}
.brand { font-size:15px; font-weight:650; letter-spacing:-.01em; white-space:nowrap; }
.brand span { color:var(--faint); font-weight:400; margin-right:2px; }
.bar nav { display:flex; gap:2px; margin-left:auto; flex-wrap:wrap; }
.bar nav a {
  padding:7px 13px; border-radius:8px; color:var(--dim); font-size:14px;
  transition:color .15s, background .15s;
}
.bar nav a:hover { color:var(--ink); background:var(--panel); }
.bar nav a.on { color:var(--gold); background:var(--panel); }

main { max-width:940px; margin:0 auto; padding:48px 28px 96px; }
main.wide { max-width:1160px; }
footer {
  max-width:940px; margin:0 auto; padding:26px 28px 48px;
  border-top:1px solid var(--line); color:var(--faint); font-size:13px;
  display:flex; gap:16px; flex-wrap:wrap; justify-content:space-between;
}

/* ---------------------------------------------------------------- type */
h1 { font-size:34px; line-height:1.25; margin:0 0 12px; letter-spacing:-.025em; font-weight:680; }
h2 { font-size:15px; margin:0 0 16px; letter-spacing:.03em; font-weight:600; color:var(--dim); }
h2 em, h1 em {
  font-style:normal; color:var(--faint); font-weight:400; font-size:.85em; margin-left:6px;
}
h2 .muted { font-weight:400; }
h3 { font-size:14px; margin:22px 0 10px; color:var(--dim); font-weight:600; }
h3 .muted { font-weight:400; font-size:12.5px; }
section { margin:44px 0; }
p { margin:0 0 14px; }
.lead { font-size:17px; line-height:1.75; color:var(--dim); max-width:62ch; margin-bottom:0; }
.sub { color:var(--dim); font-size:14px; max-width:70ch; }
.muted { color:var(--faint); }
.small { font-size:13px; }
.good { color:var(--good); } .bad { color:var(--bad); }
code {
  font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;
  background:var(--panel2); padding:2px 7px; border-radius:6px; color:#cfd8e6;
  border:1px solid var(--line);
}
.links { display:flex; gap:16px; }
.links a, main p a { color:var(--gold); border-bottom:1px solid rgba(224,176,85,.28); }
main p a:hover { border-bottom-color:var(--gold); }

.page-head { margin-bottom:40px; }
.kicker {
  font-size:12px; letter-spacing:.14em; color:var(--gold); margin:0 0 10px;
  text-transform:uppercase; font-weight:600;
}
.crumb { display:flex; gap:8px; color:var(--faint); font-size:13px; margin:0 0 14px; }
.crumb a { color:var(--dim); }
.crumb a:hover { color:var(--ink); }
.crumb span::before { content:"/"; margin-right:8px; color:var(--line2); }
.page-head.out h1 { color:var(--out); } .page-head.vil h1 { color:var(--vil); }
.page-head.und h1 { color:var(--und); } .page-head.pig h1 { color:var(--pig); }

/* ---------------------------------------------------------------- hero */
.hero { position:relative; margin:-8px 0 56px; padding:56px 0 0; }
.hero::before {
  content:""; position:absolute; inset:-48px -50vw 0; pointer-events:none;
  background:
    radial-gradient(70ch 40ch at 30% 0%, rgba(224,176,85,.09), transparent 70%),
    linear-gradient(transparent 0, var(--bg) 100%);
}
.hero > * { position:relative; }
.hero h1 { font-size:52px; letter-spacing:-.035em; margin-bottom:18px; }
.hero .lead { font-size:18px; max-width:56ch; }
.cta { display:flex; gap:10px; margin:26px 0 0; flex-wrap:wrap; }
.btn {
  padding:11px 20px; border-radius:10px; background:var(--gold); color:#1c1508;
  font-weight:650; font-size:14px; transition:transform .12s, filter .15s;
}
.btn:hover { filter:brightness(1.08); transform:translateY(-1px); }
.btn.ghost { background:transparent; color:var(--ink); border:1px solid var(--line2); }
.btn.ghost:hover { border-color:var(--faint); }
.strip {
  display:flex; gap:36px; flex-wrap:wrap; margin-top:44px; padding-top:26px;
  border-top:1px solid var(--line);
}
.strip div { display:flex; flex-direction:column; gap:1px; }
.strip b { font-size:24px; font-weight:650; letter-spacing:-.02em;
           font-variant-numeric:tabular-nums; }
.strip span { font-size:12px; color:var(--faint); }

/* ---------------------------------------------------------------- cards */
.race-grid { display:grid; gap:12px; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); }
.race-card {
  position:relative; display:block; padding:22px 20px 18px; border-radius:var(--r);
  background:var(--panel); border:1px solid var(--line); overflow:hidden;
  transition:border-color .16s, transform .16s, background .16s;
}
.race-card:hover { border-color:var(--line2); background:var(--panel2); transform:translateY(-2px); }
.race-card .rule { position:absolute; inset:0 0 auto 0; height:2px; }
.race-card.out .rule { background:var(--out); } .race-card.out h3 { color:var(--out); }
.race-card.vil .rule { background:var(--vil); } .race-card.vil h3 { color:var(--vil); }
.race-card.und .rule { background:var(--und); } .race-card.und h3 { color:var(--und); }
.race-card.pig .rule { background:var(--pig); } .race-card.pig h3 { color:var(--pig); }
.race-card h3 { margin:0 0 9px; font-size:18px; font-weight:660; letter-spacing:-.01em; }
.race-card p { color:var(--dim); font-size:13.5px; line-height:1.7; margin:0; }
.race-card.big p { min-height:4.2em; }
.race-card .meta {
  display:flex; gap:14px; margin-top:16px; padding-top:13px;
  border-top:1px solid var(--line); color:var(--faint); font-size:12px;
}

/* ---------------------------------------------------------------- steps */
.steps {
  list-style:none; margin:0; padding:0; counter-reset:s;
  display:grid; gap:1px; background:var(--line); border:1px solid var(--line);
  border-radius:var(--r); overflow:hidden;
}
.steps li {
  counter-increment:s; background:var(--panel); padding:16px 20px;
  display:grid; grid-template-columns:26px 92px 1fr; gap:14px; align-items:baseline;
}
.steps li::before {
  content:counter(s,decimal-leading-zero); color:var(--faint);
  font:600 12px/1.6 ui-monospace,monospace;
}
.steps b { font-weight:640; }
.steps span { color:var(--dim); font-size:14px; }

.split { display:grid; gap:36px; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); }
.split.tight { gap:24px; }
.split p { color:var(--dim); font-size:14.5px; }

/* ---------------------------------------------------------------- tables */
.tablewrap { overflow-x:auto; border-radius:var(--r); border:1px solid var(--line); }
table { width:100%; border-collapse:collapse; font-size:14px; }
.cmds, .keys, .facts {
  background:var(--panel); border:1px solid var(--line);
  border-radius:var(--r); overflow:hidden;
}
.list { background:var(--panel); }
th, td { text-align:left; padding:10px 14px; border-bottom:1px solid var(--line); font-weight:400; }
thead th {
  color:var(--faint); font-size:12px; letter-spacing:.03em; background:var(--bg2);
  position:sticky; top:60px; z-index:1;
}
tbody tr:last-child > * { border-bottom:0; }
tbody tr:hover { background:var(--panel2); }
.list a { font-weight:620; }
.list a:hover { color:var(--gold); }
.num { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
.note { color:var(--dim); font-size:13.5px; }
.keys th { color:var(--ink); font-weight:600; }
.facts th { color:var(--faint); font-weight:400; width:126px; }
.keys td:first-child { width:52px; }
.cmds th { white-space:nowrap; width:1%; font-weight:600; }
.cmds td:first-child { white-space:nowrap; width:1%; }

kbd {
  display:inline-block; min-width:24px; text-align:center; padding:3px 8px;
  border-radius:6px; background:var(--panel2); border:1px solid var(--line2);
  box-shadow:0 1px 0 var(--line2); font:600 12.5px/1.4 ui-monospace,monospace;
}

/* ---------------------------------------------------------------- bits */
.statgrid {
  display:grid; gap:1px; background:var(--line); border:1px solid var(--line);
  border-radius:var(--r); overflow:hidden; margin-bottom:14px;
  grid-template-columns:repeat(auto-fit,minmax(112px,1fr));
}
.stat { background:var(--panel); padding:14px 16px; display:flex; flex-direction:column; gap:2px; }
.stat span { font-size:12px; color:var(--faint); }
.stat b { font-size:19px; font-weight:640; font-variant-numeric:tabular-nums;
          letter-spacing:-.01em; }
.stat i { font-style:normal; font-size:11.5px; color:var(--faint); }

.pill {
  display:inline-block; padding:3px 10px; margin:0 4px 4px 0; border-radius:999px;
  font-size:12px; background:var(--panel2); color:var(--dim);
  border:1px solid var(--line); cursor:pointer; font-family:inherit;
  transition:border-color .14s;
}
.pill.out { color:var(--out); } .pill.vil { color:var(--vil); }
.pill.und { color:var(--und); } .pill.pig { color:var(--pig); }
.pill.on { background:var(--gold); color:#1c1508; border-color:var(--gold); }
button.pill:hover { border-color:var(--line2); }
.pills { line-height:2.1; margin:0; }
.chips { display:flex; flex-wrap:wrap; gap:6px; }
.chip {
  display:inline-flex; align-items:center; gap:6px; padding:6px 12px; border-radius:9px;
  background:var(--panel); border:1px solid var(--line); font-size:13.5px;
  transition:border-color .14s, background .14s;
}
.chip:hover { border-color:var(--line2); background:var(--panel2); }
.chip em { font-style:normal; color:var(--faint); font-size:11.5px; }
.tier-row { display:grid; grid-template-columns:34px 1fr; gap:10px; align-items:start;
            margin-bottom:9px; }
.tier-row .t { color:var(--faint); font:600 12px/2.2 ui-monospace,monospace; }
.tier-row > div { display:flex; flex-wrap:wrap; gap:6px; }
.tier {
  display:inline-block; padding:1px 7px; border-radius:5px; background:var(--panel2);
  border:1px solid var(--line2); font:600 11.5px/1.6 ui-monospace,monospace; color:var(--dim);
}
.tier.t4 { color:var(--gold); border-color:rgba(224,176,85,.4); }
.tier.t5 { color:var(--gold); background:rgba(224,176,85,.14); border-color:var(--gold); }
.tags { line-height:2.2; margin:10px 0 0; }
.tag {
  display:inline-block; padding:3px 9px; margin-right:5px; border-radius:6px;
  background:var(--panel2); color:var(--dim); font-size:12px; border:1px solid var(--line);
}
.tag.off { color:var(--bad); border-color:rgba(224,130,120,.3); }

.r i { font-style:normal; font-size:12.5px; white-space:nowrap; margin-right:9px; }
.r i:last-child { margin-right:0; }
.r .ore { color:var(--ore); } .r .food { color:var(--food); } .r .wood { color:var(--wood); }

ul.good, ul.bad { margin:0; padding-left:17px; }
ul.good li { color:var(--good); } ul.bad li { color:var(--bad); }
ul.good li, ul.bad li { margin-bottom:3px; }

.filter { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin:0 0 16px; }
#q {
  flex:1 1 180px; min-width:150px; padding:10px 14px; border-radius:10px;
  background:var(--panel); border:1px solid var(--line); color:var(--ink);
  font:inherit; font-size:14px;
}
#q:focus { outline:none; border-color:var(--line2); background:var(--panel2); }
.filter .races { display:flex; flex-wrap:wrap; }
.count { color:var(--faint); font-size:12.5px; font-variant-numeric:tabular-nums; }

@media (max-width:720px) {
  main { padding:32px 18px 64px; }
  .bar { padding:10px 18px; }
  .hero { padding-top:28px; }
  .hero h1 { font-size:38px; }
  .hero .lead, .lead { font-size:16px; }
  h1 { font-size:27px; }
  .strip { gap:24px; }
  .steps li { grid-template-columns:22px 1fr; }
  .steps li b, .steps li span { grid-column:2; }
  thead th { position:static; }
  table { font-size:13px; }
  th, td { padding:8px 10px; }
}
"""

if __name__ == "__main__":
    build()
