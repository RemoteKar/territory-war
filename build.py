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
import glob
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
    ("battles.html", "전투 기록"),
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

    battles(load_battles())
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
        unit_page(u, builds, units)
    research(doc)

    n = sum(len(f) for _, _, f in os.walk(OUT))
    print("built %d files into %s" % (n, OUT))


def load_battles():
    """Every record the server has written, newest first."""
    out = []
    for p in sorted(glob.glob(os.path.join(HERE, "data", "battles", "*.json")), reverse=True):
        try:
            out.append(json.load(io.open(p, encoding="utf-8")))
        except ValueError:
            continue
    return out


def roster(items):
    if not items:
        return '<span class="muted">-</span>'
    bits = []
    for x in items:
        ranks = x.get("levels") or {}
        veteran = sum(v for k, v in ranks.items() if k != "Lv1")
        tail = '<em>계급 %d</em>' % veteran if veteran else ""
        bits.append('<span class="chip">%s <b>%d</b>%s</span>'
                    % (e(x["korean"]), x["count"], tail))
    return '<div class="chips">%s</div>' % "".join(bits)


def battles(records):
    """One card a battle, one block a side.

    Written as a list of sides rather than attacker-against-defender because the game
    groups armies by battleId and puts no ceiling on how many share one - an ally that
    marches in is simply another side, and a two-column table could not have held it.
    """
    if not records:
        body = """
<header class="page-head">
  <p class="kicker">전투 기록</p>
  <h1>아직 없다</h1>
  <p class="lead">서버가 전투를 치르면 여기 쌓인다. 야전 조우와 정착지 공방 둘 다,
     양쪽이 무엇을 들고 왔고 무엇이 남았는지까지.</p>
</header>"""
        write("battles.html", page(0, "전투 기록", body, "battles.html"))
        return

    cards = ""
    for b in records:
        sides = ""
        for s0 in b["sides"]:
            won = s0.get("won")
            studies = []
            for k, v in (s0.get("research") or {}).items():
                studies.append("%s Lv%d" % (k, v))
            studies += list(s0.get("labs") or [])
            studies += list(s0.get("doctrines") or [])
            who = s0.get("player") or ("AI" if s0.get("ai") else "-")
            sides += """
      <div class="side%s">
        <div class="who"><b>%s</b><span>%s · %s</span>%s</div>
        <table class="facts"><tbody>
          <tr><th>데려온 병력</th><td>%d</td></tr>
          <tr><th>도중 증원</th><td>%s</td></tr>
          <tr><th>생존</th><td>%d</td></tr>
          <tr><th>손실</th><td>%d</td></tr>
          <tr><th>무기고</th><td>Lv%d</td></tr>
        </tbody></table>
        <h4>편성</h4>%s
        %s
        <h4>생존</h4>%s
        %s
      </div>""" % (
                " won" if won else "",
                e(s0["nation"]), e(who), e(s0["race"]),
                '<i class="crown">승</i>' if won else "",
                s0["brought"],
                ("<b>%d</b>" % s0["arrivedLater"]) if s0["arrivedLater"] else "0",
                s0["survived"], s0["lost"], s0.get("armouryLevel", 0),
                roster(s0.get("opening")),
                ("<h4>증원 · 생산</h4>%s" % roster(s0.get("reinforced")))
                if s0.get("reinforced") else "",
                roster(s0.get("survivors")),
                ('<p class="muted small">연구 : %s</p>' % e(" · ".join(studies)))
                if studies else "")
        cards += """
  <article class="battle">
    <header>
      <span class="tag">%s</span>
      <h2>%s</h2>
      <span class="muted small">%s · %d초</span>
    </header>
    <div class="sides">%s</div>
  </article>""" % (e(b["kind"]), e(b.get("where") or "-"),
                   e((b.get("closed") or "")[:16].replace("T", " ")),
                   b.get("seconds", 0), sides)

    body = """
<header class="page-head">
  <p class="kicker">전투 기록</p>
  <h1>치러진 싸움 <em>%d</em></h1>
  <p class="lead">서버가 스스로 적어 둔 것들이다. 양쪽이 무엇을 데려왔고 도중에 무엇이
     더 왔으며 무엇이 남았는지, 그때 어떤 연구가 끝나 있었는지까지.</p>
</header>
%s
""" % (len(records), cards)
    write("battles.html", page(0, "전투 기록", body, "battles.html", wide=True))


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
       자기 데이터를 그대로 뱉는다. 이 페이지들은 그것만 읽어 만들어지니
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


# How each people actually plays, which no table was ever going to say.
#
# The page used to open on seven yes/no rows - 민간인 있음, 자연 증가 없음 - and a reader
# who did not already know the game learned nothing from them. A row can hold the fact
# that a warband has no civilians. It cannot say that this is the whole of why a warband
# raids, or that losing the pens costs it the next generation rather than a building.
PLAYSTYLE = {
    "OUTLANDER": [
        "무엇 하나 특별히 잘하지 않는 대신 못하는 것도 없다. 사람을 뽑아 아무 일에나 "
        "붙이고 밭도 광산도 병영도 전부 자기 손으로 짓는다. 지형이 나쁘면 그 지형에 "
        "맞는 건물을 올려 답한다. 사막에는 선인장 농장, 호수에는 낚시터. 다른 세 "
        "종족은 못 하는 일.",

        "연구소와 대학은 이들만의 것. 연구소는 다섯 갈래에서 하나씩만 고르게 하니 "
        "무엇을 포기할지가 곧 노선이 된다. 대학은 병종별 교리를 가르쳐 이미 세워둔 "
        "부대까지 소급해 바꾼다. 정책도 이들만 고른다. 건국 정책 하나에 노선 셋. "
        "합쳐 넷을 정하고 그대로 간다.",

        "병사 하나하나가 다르다. 태어날 때 굴려 받는 자질이 여섯. 체력·공격력·속도· "
        "공격 속도·노동력·기술이고 목장이 그 하한을 밀어올리며 대학이 상한을 연다. "
        "싸워서 죽인 만큼 계급이 오르고 계급은 체력과 공격력을 더한다. 살려 둔 병사가 "
        "새로 뽑은 병사보다 비싼 이유. 계급은 민간인으로 돌아가도 남는다.",

        "약점은 값. 남들이 종족 특성으로 공짜로 얻는 것을 이들은 전부 자원과 시간으로 "
        "산다. 인구가 저절로 늘어나는 만큼 먹이기도 해야 한다. 병사 하나를 뽑을 "
        "때마다 밭에서 한 명이 빠진다. 판을 길게 끌수록 유리한 쪽.",
    ],
    "VILLAGER": [
        "번식으로 늘어나고 한 번 배운 직업은 바뀌지 않는다. 그래서 무엇을 짓느냐가 곧 "
        "어떤 마을이 되느냐를 정한다. 밀밭과 에메랄드 광산과 제재소, 셋이 경제의 전부. "
        "지형별 특산 농장은 없다. 땅이 나쁘면 다른 걸 짓는 대신 다른 데로 간다.",

        "병영이 없다. 주민은 스스로 싸우지 않고 용병 시장에서 사람을 산다. 용병은 "
        "인구를 쓰지 않고 임금으로 유지되니 인구 한도와 병력 규모가 서로 발목을 잡지 "
        "않는다. 대신 세울 수 있는 것이 골렘과 우민. 종루에 우민을 올리면 사거리가 "
        "늘어난다.",

        "연구소도 대학도 없어 기술 트리가 통째로 비어 있다. 그 대가로 연구가 걸린 "
        "건물 레벨 제한을 받지 않는다. 밀밭이든 주민 집이든 자원만 있으면 Lv4까지 그냥 "
        "올라간다. 고를 정책도 없는 종족. 그만큼 판이 단순하고 손이 덜 간다.",
    ],
    "UNDEAD": [
        "먹지 않고 낳지 않는다. 식량 건물이 아예 없고 집도 짓지 않는다. 늘어나는 길은 "
        "하나뿐. 전장을 지키고 남은 시체를 거두는 것이다. 이겨도 물러나면 시체를 "
        "놓치니 이 종족에게 후퇴는 병력 손실과 같은 말이다.",

        "납골당이 소유할 수 있는 시체 수를 정하고 그게 곧 병력 상한이다. 제단에서 "
        "유해를 일으켜 병사를 세우는데 소생체는 계급도 능력치도 물려받지 않는다. "
        "치료도 되지 않는다. 부서지면 그걸로 끝. 다시 일으키는 수밖에 없다.",

        "굶지 않으니 보급 걱정 없이 멀리 나간다. 인구도 안 먹고 집도 안 짓는 만큼 "
        "자원이 통째로 군비로 간다. 초반이 느리고 전장을 한 번 잡으면 눈덩이처럼 "
        "불어나는 쪽. 첫 싸움에서 밀리면 회복할 방법이 마땅치 않다.",
    ],
    "PIGLIN": [
        "민간인과 병사가 같은 몸이다. 징집이라는 절차가 없고 병사를 뽑으면 그 값을 "
        "치를 뿐이다. 번식도 하지 않는다. 늘어나는 유일한 길은 남의 주민을 잡아와 "
        "수용소에 가두는 것. 이 종족에게 전쟁은 인구 정책이기도 하다.",

        "광물을 캐지 못한다. 이들에게 광물은 금이고 금은 교역소에서 목재와 식량을 "
        "바꿔 얻는다. 환율이 나쁘니 금이 드는 것은 전부 비싸다. 건물은 전부 목재라 "
        "벌목대가 곧 국력. 괴수 우리 하나가 대장간과 마굿간을 겸한다.",

        "자질과 계급은 피글린 병사에게만 붙는다. 전사와 브루트는 여섯 자질을 굴려 "
        "받고 싸운 만큼 계급이 오른다. 우리에서 사 오는 괴수는 전부 평균값 고정에 "
        "계급도 오르지 않는다. 호글린 열 마리는 언제나 똑같은 호글린 열 마리.",

        "괴수 우리 레벨이 호글린에서 블레이즈, 가스트, 위더 순으로 열린다. 연구소가 "
        "없어 연구 없이 Lv4까지 올라가니 자원만 모으면 최상위 병종에 닿는다. 병사가 "
        "곧 인부. 군대를 놀려두면 경제가 살고 내보내면 건설이 멈춘다. 그 줄타기가 이 "
        "종족의 전부.",
    ],
}


def race_page(r, builds, units):
    rid = r["id"]
    prose = "".join("<p>%s</p>" % t for t in PLAYSTYLE.get(rid, []))
    facts = [
        ("무기고 계열", builds[r["armoury"]]["korean"]),
        ("주거 계열", builds[r["quarters"]]["korean"]),
        ("연구", "연구소·대학" if r["researches"] else "없음 · 건물 Lv4 제한 면제"),
        ("인구", "번식" if r["growsOnItsOwn"] else
                 ("시체 수급" if r["reapsRemains"] else "포로")),
        ("병력", "징집" if r["keepsCivilians"] else "값을 치러 얻음"),
        ("배급", "x%s" % r["ration"]),
        ("정책", "고름" if r["choosesPolicy"] else "없음"),
    ]
    ft = "".join('<div class="stat"><span>%s</span><b>%s</b></div>'
                 % (e(a), e(b)) for a, b in facts)

    chips = "".join(
        '<a class="chip" href="../building/%s.html">%s</a>' % (i, e(builds[i]["korean"]))
        for i in r["buildings"])

    ulist = ""
    for tier in range(1, 6):
        row = [i for i in r["units"] if units[i]["tier"] == tier]
        if not row:
            continue
        # Yellow for ground a nation has to hold first, blue for a study it has to
        # finish. Both are conditions on top of the armoury level, and a flat list of
        # names said nothing about either.
        def chip(i):
            x = units[i]
            cls = "chip"
            note = ""
            if x.get("needsGround"):
                cls += " ground"
                note = x.get("homeland") or "해안"
            elif x.get("needsLab"):
                cls += " study"
                note = x["needsLab"]
            return '<a class="%s" href="../unit/%s.html">%s%s</a>' % (
                cls, i, e(x["korean"]),
                '<em>%s</em>' % e(note) if note else "")

        ulist += '<div class="tier-row"><span class="t">T%d</span><div>%s</div></div>' % (
            tier, "".join(chip(i) for i in row))

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

<section class="playstyle"><h2>어떻게 노는 종족인가</h2>%s</section>

<section><h2>한눈에</h2><div class="statgrid wide-stat">%s</div></section>

<section><h2>지을 수 있는 건물 <em>%d</em></h2><div class="chips">%s</div></section>

<section><h2>뽑을 수 있는 병종 <em>%d</em></h2>%s
  <p class="legend"><span class="chip ground">지형·해안 필요</span>
     <span class="chip study">연구 필요</span></p></section>

<section><h2>정책 <em>%d</em></h2><table class="cmds"><tbody>%s</tbody></table></section>
""" % (e(r["korean"]), RACE_TAG[rid], e(r["korean"]), e(r["blurb"]), prose, ft,
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


def trait(a):
    """A chip short enough to scan, with the explanation on hover.

    The game writes an ability as a name and a qualifier in one string - "퇴마 - 언데드·
    강령술사에 추가 피해", "마법 공격 (방어력 무시)" - which is right for a chat line and
    far too long for a row of chips. Split at the separator the game already uses and hang
    the tail off a tooltip. title= carries it as well, so it survives touch and a reader.
    """
    label, tip = a, ""
    for sep in (" - ", " — "):
        if sep in a:
            label, tip = a.split(sep, 1)
            break
    else:
        m = re.match(r"^(.*?)\s*\((.+)\)$", a)
        if m:
            label, tip = m.group(1), m.group(2)
    if not tip:
        return '<span class="tag able">%s</span>' % e(a)
    return ('<span class="tag able tip" data-tip="%s" title="%s">%s</span>'
            % (e(tip), e(tip), e(label)))


def unit_page(u, builds, units):
    def pct(x):
        return "%d%%" % round(x * 100)

    stats = [("체력", str(u["maxHp"]), ""),
             ("공격력", str(u["damage"]), ""),
             ("방어력", str(u.get("armour", 0)), ""),
             ]
    # A shooter's rate is its reload; secondsPerBlow describes a melee swing it may never
    # make. Both, for the ones that do both.
    # A unit that deals no damage has no rate worth printing. A cleric's one-second swing
    # is the animation, not a thing that happens to anybody.
    if u["damage"] > 0 or u.get("meleeDamage"):
        # Called 공속 because that is what the barracks card calls it. The two now carry
        # the same number - the site had it at half for a while - and a player checking one
        # against the other should not have to work out that 재장전 and 공속 are the same
        # thing said twice.
        two = u["ranged"] and u["hybrid"]
        if u["ranged"]:
            stats.append(("사격 공속" if two else "공속",
                          "%s초" % u.get("reloadSeconds", 0), "1발당"))
        if not u["ranged"] or u["hybrid"]:
            stats.append(("근접 공속" if two else "공속",
                          "%s초" % u.get("secondsPerBlow", 0), "1회당"))
    stats += [
             ("사거리", str(u["range"]), ""),
             ("이동", str(u["blocksPerSecond"]), "블록/초"),
             ("유지비", str(u["upkeep"]), "")]
    if u.get("accuracyBand") and u["damage"] > 0:
        stats.append(("명중률", u["accuracyBand"], ""))
    for key, label, note in [("crit", "치명타율", ""), ("evasion", "회피율", ""),
                             ("block", "방어 확률", ""), ("magicResist", "마법 저항", ""),
                             ("pierceArmour", "방어 관통", "")]:
        v = u.get(key) or 0
        if v:
            stats.append((label, pct(v), note))
    # 기술 is derived from the tier and reads 10 for eighty-two of the hundred and two,
    # so on a page it is a column of the same number. Left out of the sheet.
    if (u.get("chargeBonus") or 1) > 1:
        stats.append(("돌격 배수", "x%s" % u["chargeBonus"], ""))
    if (u.get("salvo") or 1) > 1:
        stats.append(("연사", "%d발" % u["salvo"], "쿨 한 번에"))
    if u.get("windUp"):
        stats.append(("준비 동작", "%s초" % u["windUpSeconds"], "발사 전"))
    # Who it walks at when several are within reach.
    if u.get("priority") and u["damage"] > 0:
        stats.append(("공격 우선도", u["priority"], ""))
    if u["residents"] != 1:
        stats.append(("차지 인구", "%d명" % u["residents"], ""))
    if u["hireCost"]:
        stats.append(("임금", str(u["hireCost"]), "용병"))
    grid = "".join(
        '<div class="stat"><span>%s</span><b>%s</b>%s</div>'
        % (e(a), e(v), "<i>%s</i>" % e(n) if n else "") for a, v, n in stats)

    # Damage a second, worked out from the two numbers already on the sheet.
    #
    # A sheet that gives a blow and an interval separately leaves the reader multiplying,
    # and the two are not comparable across a musket and a dagger until somebody does.
    # Armour, matchup and research all land later in the real thing, so this is the figure
    # before any of them - said plainly rather than dressed up as the truth.
    rate = ""
    span = u["reloadSeconds"] if u["ranged"] else u["secondsPerBlow"]
    if u["damage"] > 0 and span:
        label = "사격 초당 피해" if u.get("meleeAttack") else "초당 피해"
        rows = [(label, "%.1f" % (u["damage"] / span),
                 "공격력 %d ÷ 공속 %s초" % (u["damage"], span))]
        # The blade keeps its own clock: secondsPerBlow, not the reload it does not use.
        blow = u.get("secondsPerBlow")
        if u.get("meleeAttack") and u.get("meleeDamage") and blow:
            rows.append(("근접 초당 피해", "%.1f" % (u["meleeDamage"] / blow),
                         "공격력 %d ÷ 공속 %s초" % (u["meleeDamage"], blow)))
        mate = units.get(u.get("crew")) if u.get("crew") else None
        if mate and mate["damage"] > 0:
            ms = mate["reloadSeconds"] if mate["ranged"] else mate["secondsPerBlow"]
            if ms:
                rows.append(("한 기 합계",
                             "%.1f" % (u["damage"] / span + mate["damage"] / ms),
                             "조종 + 탑승"))
        if (u.get("salvo") or 1) > 1:
            rows.append(("볼리 합계", "%d" % (u["damage"] * u["salvo"]),
                         "%d발 전탄 명중 시" % u["salvo"]))
        if u.get("splash"):
            rows.append(("인접 피해", "%d%%" % round(u["splash"] * 100), "함께 들어감"))
        if (u.get("chargeBonus") or 1) > 1:
            rows.append(("돌격 시", "%.1f" % (u["damage"] * u["chargeBonus"]), "한 번의 피해"))
        rate = ('<section><h2>실제 성능</h2><div class="statgrid">%s</div>'
                '<p class="muted small">방어력·상성·연구를 적용하기 전 값이다.</p>'
                '</section>'
                % "".join('<div class="stat"><span>%s</span><b>%s</b><i>%s</i></div>'
                          % (e(a), e(v), e(n)) for a, v, n in rows))

    # The animal under the rider, which fights on its own account.
    #
    # maul lands in the same swing as the rider's, so the rate and the reach are his -
    # what differs is that the beast gets neither the charge multiplier nor a crit. Two
    # attackers in one exchange, and only one of them was on the page.
    beast = ""
    if u.get("maul"):
        cells = [("피해", str(u["maul"]), "한 번에"),
                 ("공속", "%s초" % u.get("secondsPerBlow"), "기수와 같은 타격"),
                 ("사거리", str(u["range"]), "기수와 같음")]
        beast = ('<section><h2>탑승물 공격</h2><div class="statgrid">%s</div>'
                 '<p class="muted small">기수가 휘두르는 같은 박자에 짐승도 문다. '
                 '방어력은 똑같이 적용되지만 돌격 배수와 치명타는 붙지 않는다.</p>'
                 '</section>'
                 % "".join('<div class="stat"><span>%s</span><b>%s</b><i>%s</i></div>'
                           % (e(a), e(v), e(n)) for a, v, n in cells))

    # What it mends, and how often. Two clocks, and which one matters is the whole of
    # how a witch plays differently from a cardinal.
    mend = ""
    rows = []
    if u.get("healing"):
        rows.append(("회복량", str(u["healing"]), "한 번에"))
        rows.append(("간격", "%s초" % u.get("healSeconds"), "가장 다친 아군 1명"))
    if u.get("mendRadius"):
        rows.append(("회복량", str(u["mendAmount"]), "범위 안 전원"))
        rows.append(("범위", "%s블록" % u["mendRadius"], ""))
        if u.get("mendShared"):
            rows.append(("간격", "공속 공유", "축복이 공격 대신 나감"))
        else:
            rows.append(("간격", "%s초" % u.get("mendSeconds"), "공격과 별개"))
    if rows:
        note = ("체력이 70% 아래로 떨어진 아군이 있을 때만 축복을 쓴다. "
                "그래서 한 발도 못 쏘고 긁힌 상처만 치료하는 일이 없다."
                if u.get("mendShared") else
                "쏠 상대가 없어도 회복은 자기 박자대로 나간다."
                if u.get("mendRadius") else
                "사거리 안에서 가장 많이 다친 한 명을 고른다. 스스로는 싸우지 못한다.")
        mend = ('<section><h2>회복</h2><div class="statgrid">%s</div>'
                '<p class="muted small">%s</p></section>'
                % ("".join('<div class="stat"><span>%s</span><b>%s</b>%s</div>'
                           % (e(a), e(v), "<i>%s</i>" % e(n) if n else "")
                           for a, v, n in rows), note))

    # The traits the game itself keeps, plus the two it does not put in that list.
    #
    # abilities() already names 돌격 · 기마 · 장벽 도약 and a dozen more, and the page was
    # ignoring all of it in favour of six booleans. Flying is the one real gap in that
    # list - every other entry is something a soldier does and this one is where he
    # stands, so a dragon rider read as ordinary cavalry.
    tags = []
    if u.get("flies"):
        tags.append('<span class="tag fly">비행</span>')
    for a in (u.get("abilities") or []):
        tags.append(trait(a))
    for key, label in [("ranged", "원거리"), ("hybrid", "근접 겸용"),
                       ("medic", "치유"), ("hired", "용병"), ("undead", "소생체"),
                       ("militia", "민병"), ("mindless", "괴수"), ("golem", "골렘"),
                       ("summoned", "소환"), ("crewOnly", "승무원")]:
        if u.get(key):
            tags.append('<span class="tag">%s</span>' % label)
    # Only where it tells you something.
    #
    # A village fields hirelings, golems and illagers and not one of them labours, so the
    # tag was on every card in the people and said nothing about any of them. The copper
    # golem is the opposite case - the one machine built to fetch and carry, an exception
    # written into UnitType.labours by name - and that is worth a chip.
    if u["id"] == "COPPER_GOLEM":
        tags.append('<span class="tag able">노동 가능</span>')
    elif not u["labours"] and u.get("owner") != "VILLAGER":
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

    # Composed in Docs.java out of the same fields the combat code reads, so it cannot
    # describe a weapon the unit does not carry. Newlines are real line breaks.
    # What is actually strapped on, which is also what the attack line names.
    rows = []
    if u["ranged"] and u.get("weapon"):
        rows.append(("사격 무기", u["weapon"]))
    melee = u.get("meleeWeapon")
    if (not u["ranged"] or u["hybrid"]) and melee:
        rows.append(("근접 무기", melee))
    if not rows and u.get("mainHand"):
        rows.append(("장비", u["mainHand"]))
    off = u.get("offhand")
    if off and off not in (u.get("weapon"), melee):
        rows.append(("보조 손", off))
    gear = "".join("<tr><th>%s</th><td>%s</td></tr>" % (e(a), e(v)) for a, v in rows)

    def block(title, text):
        if not text:
            return ""
        rows = "".join("<p>%s</p>" % e(x) for x in text.split("\n") if x.strip())
        return '<section class="attack"><h2>%s</h2>%s</section>' % (title, rows)

    # Two weapons, two blocks. A mercenary shoots or it fights; neither is a note on the
    # other, and the melee one was reading as a footnote while it shared the paragraph.
    hybrid = bool(u.get("meleeAttack"))
    attack = block("사격 공격" if hybrid else "공격 방식", u.get("attack"))
    attack += block("근접 공격", u.get("meleeAttack"))

    # Two on one mount, two sets of numbers.
    #
    # A balloon carries an archer and a camel rider carries a second bow. The crewman is
    # crewOnly so he never gets a page of his own, and the page for the thing they ride
    # was quoting one seat's damage as though that were the unit.
    seats = ""
    mate = units.get(u.get("crew")) if u.get("crew") else None
    if mate:
        def seat(x, who):
            bits = [("체력", x["maxHp"]), ("공격력", x["damage"]), ("사거리", x["range"])]
            if x.get("accuracyBand"):
                bits.append(("명중률", x["accuracyBand"]))
            if x.get("weapon"):
                bits.append(("장비", x["weapon"]))
            return ('<div class="seat"><h3>%s <span class="muted">%s</span></h3>'
                    '<div class="statgrid">%s</div></div>'
                    % (e(who), e(x["korean"]),
                       "".join('<div class="stat"><span>%s</span><b>%s</b></div>'
                               % (e(a), e(v)) for a, v in bits)))
        seats = ('<section><h2>탑승 인원 <em>2</em></h2>'
                 '<p class="sub">한 기에 둘이 탄다. 아래쪽은 따로 뽑을 수 없고 '
                 '이 병종에 딸려 온다.</p>%s%s</section>'
                 % (seat(u, "조종"), seat(mate, "탑승")))

    match = ""
    if u["strongAgainst"] or u["weakAgainst"]:
        match = """
<section><h2>상성</h2><div class="split tight">
  <div><h3 class="good">유리</h3>%s</div>
  <div><h3 class="bad">불리</h3>%s</div>
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
%s
<section><h2>제원</h2><div class="statgrid">%s</div>
<table class="facts"><tbody>%s<tr><th>비용</th><td>%s</td></tr></tbody></table></section>
%s
%s
%s
%s
%s
%s
%s
""" % (e(u["korean"]), e(u["korean"]), u["tier"], u["tier"], e(u["role"]),
       u["trainedAt"], e(builds[u["trainedAt"]]["korean"]),
       "".join(tags), race_pills(u["fieldableBy"], "../"), attack, grid, gear,
       cost(u["cost"]), beast, rate, mend, seats, lim, match, ups)
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

.seat h3 { margin:18px 0 8px; color:var(--ink); }
.seat h3 .muted { font-weight:400; }
.chip.ground { border-color:rgba(224,176,85,.45); color:var(--gold); }
.chip.study { border-color:rgba(121,166,232,.45); color:var(--out); }
.chip.ground em, .chip.study em { color:inherit; opacity:.7; }
.legend { display:flex; gap:8px; margin-top:14px; }
.legend .chip { cursor:default; font-size:12px; padding:3px 9px; }

.battle {
  background:var(--panel); border:1px solid var(--line); border-radius:var(--r);
  padding:20px; margin-bottom:16px;
}
.battle > header { display:flex; gap:12px; align-items:baseline; flex-wrap:wrap;
                   margin-bottom:16px; }
.battle > header h2 { margin:0; color:var(--ink); font-size:17px; }
.sides { display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); }
.side { background:var(--bg2); border:1px solid var(--line); border-radius:10px; padding:16px; }
.side.won { border-color:rgba(224,176,85,.5); }
.side .who { display:flex; gap:8px; align-items:baseline; flex-wrap:wrap; margin-bottom:12px; }
.side .who b { font-size:16px; }
.side .who span { color:var(--faint); font-size:12.5px; }
.crown { font-style:normal; background:var(--gold); color:#1c1508; font-size:11px;
         padding:1px 7px; border-radius:5px; font-weight:700; }
.side h4 { margin:14px 0 7px; font-size:12.5px; color:var(--faint); font-weight:500; }
.side .chip { font-size:12.5px; padding:4px 9px; }
.side .chip b { color:var(--gold); }
.side .chip em { font-style:normal; color:var(--faint); font-size:11px; margin-left:4px; }

.attack {
  border-left:2px solid var(--gold); padding:2px 0 2px 16px; margin:34px 0;
}
.attack p { color:var(--ink); font-size:15px; margin:0 0 6px; }
.attack p:last-child { margin-bottom:0; }
.attack p ~ p { color:var(--dim); font-size:14px; }

.playstyle p {
  color:var(--dim); font-size:15.5px; line-height:1.85; max-width:66ch; margin-bottom:18px;
}
.playstyle p:first-of-type { color:var(--ink); }
.statgrid.wide-stat { grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); }
.statgrid.wide-stat .stat b { font-size:15px; font-weight:600; letter-spacing:0; }

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
.tag.able { color:var(--ink); border-color:var(--line2); }
.tag.tip { position:relative; cursor:help; border-bottom:1px dashed var(--faint); }
.tag.tip::after {
  content:attr(data-tip); position:absolute; left:50%; bottom:calc(100% + 9px);
  transform:translateX(-50%); width:max-content; max-width:min(280px,70vw);
  padding:7px 11px; border-radius:9px; background:var(--panel2);
  border:1px solid var(--line2); color:var(--ink); font-size:12.5px; line-height:1.55;
  white-space:normal; text-align:left; opacity:0; pointer-events:none;
  transition:opacity .14s; z-index:9; box-shadow:0 8px 24px rgba(0,0,0,.45);
}
.tag.tip:hover::after, .tag.tip:focus-visible::after { opacity:1; }
.tag.fly { color:var(--out); border-color:rgba(121,166,232,.45); }

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
