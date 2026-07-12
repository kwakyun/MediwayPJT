from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    KeepTogether, Flowable, HRFlowable
)
from reportlab.pdfgen.canvas import Canvas
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "pdf" / "메디웨이_개발_제안서.pdf"

NAVY = HexColor("#12324A")
BLUE = HexColor("#167D9A")
TEAL = HexColor("#24A6A1")
MINT = HexColor("#E9F7F5")
SKY = HexColor("#EAF4F8")
INK = HexColor("#24333D")
GRAY = HexColor("#60727D")
LIGHT = HexColor("#F5F8FA")
LINE = HexColor("#D7E2E8")
ORANGE = HexColor("#F59E42")
RED = HexColor("#D95C5C")
WHITE = colors.white

pdfmetrics.registerFont(TTFont("Malgun", r"C:\Windows\Fonts\malgun.ttf"))
pdfmetrics.registerFont(TTFont("MalgunBold", r"C:\Windows\Fonts\malgunbd.ttf"))

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="KBody", fontName="Malgun", fontSize=9.3, leading=15, textColor=INK, spaceAfter=4))
styles.add(ParagraphStyle(name="KSmall", fontName="Malgun", fontSize=7.8, leading=12, textColor=GRAY))
styles.add(ParagraphStyle(name="KTitle", fontName="MalgunBold", fontSize=24, leading=33, textColor=NAVY, spaceAfter=12))
styles.add(ParagraphStyle(name="KSubTitle", fontName="Malgun", fontSize=11, leading=18, textColor=GRAY))
styles.add(ParagraphStyle(name="KH1", fontName="MalgunBold", fontSize=17, leading=23, textColor=NAVY, spaceBefore=2, spaceAfter=10))
styles.add(ParagraphStyle(name="KH2", fontName="MalgunBold", fontSize=11.5, leading=17, textColor=BLUE, spaceBefore=7, spaceAfter=5))
styles.add(ParagraphStyle(name="KH3", fontName="MalgunBold", fontSize=9.5, leading=14, textColor=INK, spaceAfter=3))
styles.add(ParagraphStyle(name="KWhite", fontName="Malgun", fontSize=9, leading=14, textColor=WHITE))
styles.add(ParagraphStyle(name="KWhiteBold", fontName="MalgunBold", fontSize=12, leading=17, textColor=WHITE))
styles.add(ParagraphStyle(name="KCenter", fontName="Malgun", fontSize=8.5, leading=13, alignment=TA_CENTER, textColor=INK))
styles.add(ParagraphStyle(name="KCenterBold", fontName="MalgunBold", fontSize=9, leading=13, alignment=TA_CENTER, textColor=NAVY))


def P(text, style="KBody"):
    return Paragraph(text, styles[style])


def bullets(items):
    rows = []
    for item in items:
        rows.append([P("●", "KSmall"), P(item)])
    t = Table(rows, colWidths=[5*mm, 165*mm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TEXTCOLOR", (0,0), (0,-1), TEAL),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 2),
        ("TOPPADDING", (0,0), (-1,-1), 1),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    return t


def info_box(title, body, bg=SKY, accent=BLUE, width=170*mm):
    t = Table([[P(title, "KH3")], [P(body)]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), bg),
        ("BOX", (0,0), (-1,-1), 0.5, LINE),
        ("LINEBEFORE", (0,0), (0,-1), 4, accent),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
    ]))
    return t


def section_title(number, title, subtitle=None):
    content = [P(f"{number}. {title}", "KH1")]
    if subtitle:
        content.append(P(subtitle, "KSubTitle"))
        content.append(Spacer(1, 3*mm))
    return content


def styled_table(data, widths, header=True, font_size=8.2):
    converted = []
    for r, row in enumerate(data):
        converted.append([P(str(x), "KCenterBold" if header and r == 0 else "KSmall") for x in row])
    t = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.4, LINE),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("BACKGROUND", (0,1), (-1,-1), WHITE),
    ]
    if header:
        commands += [("BACKGROUND", (0,0), (-1,0), SKY), ("LINEBELOW", (0,0), (-1,0), 1, BLUE)]
    for r in range(1 if header else 0, len(data)):
        if r % 2 == 0:
            commands.append(("BACKGROUND", (0,r), (-1,r), LIGHT))
    t.setStyle(TableStyle(commands))
    return t


class ScoreChart(Flowable):
    def __init__(self, width=170*mm, height=48*mm):
        super().__init__(); self.width=width; self.height=height
    def draw(self):
        c = self.canv
        labels = [("거리",45,BLUE),("날씨",20,TEAL),("대기질",20,ORANGE),("사용자 적합도",15,RED)]
        x0, y0, barw = 32*mm, self.height-12*mm, 125*mm
        c.setFont("MalgunBold", 9); c.setFillColor(NAVY); c.drawString(0, self.height-5*mm, "접근성 점수 가중치")
        for i,(label,val,col) in enumerate(labels):
            y=y0-i*9*mm
            c.setFont("Malgun",8); c.setFillColor(INK); c.drawRightString(x0-3*mm,y+2,label)
            c.setFillColor(HexColor("#E8EEF1")); c.roundRect(x0,y,barw,5*mm,2*mm,fill=1,stroke=0)
            c.setFillColor(col); c.roundRect(x0,y,barw*val/50,5*mm,2*mm,fill=1,stroke=0)
            c.setFont("MalgunBold",8); c.setFillColor(INK); c.drawString(x0+barw+3*mm,y+1,val.__str__()+"%")


class Architecture(Flowable):
    def __init__(self, width=170*mm, height=55*mm):
        super().__init__(); self.width=width; self.height=height
    def draw(self):
        c=self.canv
        boxes=[
            (0,"사용자 입력",["지역·위치","사용자·시설 유형"]),
            (44,"데이터 결합",["시설·날씨","대기질·인구"]),
            (88,"추천 엔진",["거리 계산","점수·이유 생성"]),
            (132,"결과 표현",["TOP 5·지도","지역 차트"]),
        ]
        for idx,(xmm,title,lines) in enumerate(boxes):
            x=xmm*mm; y=9*mm; w=36*mm; h=35*mm
            c.setFillColor(SKY if idx%2==0 else MINT); c.setStrokeColor(LINE)
            c.roundRect(x,y,w,h,3*mm,fill=1,stroke=1)
            c.setFillColor(NAVY); c.setFont("MalgunBold",9); c.drawCentredString(x+w/2,y+h-9*mm,title)
            c.setFillColor(GRAY); c.setFont("Malgun",7.5)
            for j,line in enumerate(lines): c.drawCentredString(x+w/2,y+h-18*mm-j*6*mm,line)
            if idx < 3:
                c.setStrokeColor(TEAL); c.setLineWidth(1.5)
                c.line(x+w+2*mm,y+h/2,x+w+6*mm,y+h/2)
                c.line(x+w+6*mm,y+h/2,x+w+4*mm,y+h/2+2*mm)
                c.line(x+w+6*mm,y+h/2,x+w+4*mm,y+h/2-2*mm)


def header_footer(canvas: Canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(LINE); canvas.line(20*mm, 286*mm, 190*mm, 286*mm)
        canvas.setFont("Malgun", 7.5); canvas.setFillColor(GRAY)
        canvas.drawString(20*mm, 290*mm, "메디웨이 개발 제안서")
        canvas.drawRightString(190*mm, 12*mm, str(doc.page))
        canvas.drawString(20*mm, 12*mm, "날씨·대기질 기반 생활 의료 접근성 추천 서비스")
    canvas.restoreState()


doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
                        topMargin=18*mm, bottomMargin=18*mm,
                        title="메디웨이 개발 제안서", author="메디웨이 프로젝트")
story=[]

# Cover
story += [Spacer(1, 34*mm)]
story.append(Table([[P("DEVELOPMENT PROPOSAL", "KWhiteBold")]], colWidths=[62*mm], style=TableStyle([
    ("BACKGROUND",(0,0),(-1,-1),BLUE),("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
    ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)])))
story += [Spacer(1, 10*mm), P("메디웨이", "KTitle"),
          P("날씨와 대기질을 고려한<br/>생활 의료 접근성 추천 서비스", "KTitle"),
          Spacer(1, 5*mm), P("단순히 가까운 의료기관이 아니라,<br/>사용자와 이동 환경에 맞는 의료기관을 제안합니다.", "KSubTitle"),
          Spacer(1, 24*mm), Architecture(), Spacer(1, 18*mm)]
story.append(Table([[P("제안 범위", "KWhiteBold"), P("서비스 기획 · 데이터 · 추천 모델 · UI/UX · 구현 · 검증", "KWhite")]],
                   colWidths=[38*mm,132*mm], style=TableStyle([
                       ("BACKGROUND",(0,0),(-1,-1),NAVY),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                       ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
                       ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10)])))
story.append(PageBreak())

# 1 Summary
story += section_title("01", "제안 요약", "공공데이터를 사용자의 실제 이동 의사결정에 연결하는 설명 가능한 추천 서비스")
story.append(info_box("핵심 제안", "병원·약국의 위치 정보에 날씨, 대기질, 사용자 유형을 결합하여 방문 적합도를 0~100점으로 산출하고, 추천 TOP 5와 추천 이유를 지도와 카드로 제공한다.", MINT, TEAL))
story += [Spacer(1,5*mm), P("추진 배경", "KH2"), bullets([
    "기존 의료기관 검색은 거리와 위치 중심이어서 비, 폭염, 미세먼지처럼 이동 부담을 바꾸는 조건을 충분히 설명하지 못한다.",
    "같은 거리라도 고령자와 호흡기 질환자가 체감하는 접근성은 다르다.",
    "서로 분리된 공공데이터를 사용자의 생활 속 선택에 바로 활용할 수 있는 형태로 결합할 필요가 있다."
]), Spacer(1,4*mm), P("제안 가치", "KH2")]
value_data = [
    ["가치", "제공 방식", "기대 효과"],
    ["상황 기반 추천", "거리·날씨·대기질·사용자 특성 결합", "실제 이동 부담을 반영한 비교"],
    ["설명 가능성", "구성 점수와 추천 이유 공개", "결과에 대한 이해와 신뢰 향상"],
    ["지역 인사이트", "인구 대비 의료기관 지표 제공", "개인 추천을 넘어 지역 현황 파악"],
    ["안정적 시연", "정제된 대체 데이터 포함", "외부 연결 장애에도 핵심 기능 유지"],
]
story.append(styled_table(value_data,[31*mm,68*mm,71*mm]))
story += [Spacer(1,5*mm), P("핵심 산출물", "KH2"), bullets([
    "Streamlit 기반 추천 서비스", "정제된 의료기관·날씨·대기질·인구 데이터",
    "설명 가능한 추천 점수와 이유 생성 로직", "추천·지역 분석·추천 기준 안내 화면",
    "대표 시나리오와 검증 결과", "서비스 설명 자료와 장애 대응용 시연 자료"
])]
story.append(PageBreak())

# 2 Scope and users
story += section_title("02", "서비스 범위와 사용자", "핵심 추천 흐름을 완결성 있게 구현하기 위한 명확한 범위")
scope = [
    ["구분", "범위"],
    ["대상 지역", "1개 시·군·구"],
    ["사용자 유형", "일반 사용자 · 고령자 · 호흡기 질환자"],
    ["시설 유형", "병원 · 약국"],
    ["활용 데이터", "의료기관 위치 · 날씨 · 대기질 · 인구통계"],
    ["구현 기술", "Python · Streamlit · pandas · folium/pydeck · Plotly"],
]
story.append(styled_table(scope,[38*mm,132*mm]))
story += [Spacer(1,6*mm), P("대표 사용자 시나리오", "KH2")]
scenarios = [
    ["시나리오", "조건", "서비스가 보여줄 변화"],
    ["기본 추천", "일반 사용자 · 강수 없음 · 대기질 보통", "거리의 영향이 중심이 되어 가까운 시설이 우선된다."],
    ["이동 부담", "고령자 · 비", "짧은 이동거리의 중요성이 추천 이유에 명확히 반영된다."],
    ["호흡기 민감", "호흡기 질환자 · 미세먼지 나쁨", "짧은 이동과 관련 진료과목이 함께 반영된다."],
]
story.append(styled_table(scenarios,[32*mm,54*mm,84*mm]))
story += [Spacer(1,6*mm), P("핵심 사용자 흐름", "KH2"), Architecture(), Spacer(1,2*mm)]
story.append(info_box("서비스 한계의 명확한 표현", "본 서비스는 의료적 진단이나 진료 적합성을 판단하지 않는다. 공공데이터를 활용한 이동 접근성 비교 결과이며 실제 운영 및 진료 가능 여부는 해당 기관에 별도로 확인하도록 안내한다.", LIGHT, ORANGE))
story.append(PageBreak())

# 3 Data and scoring
story += section_title("03", "데이터와 추천 모델", "네 종류의 공공데이터를 하나의 지역과 좌표 기준으로 결합")
data_tbl = [
    ["데이터", "핵심 내용", "주요 컬럼", "활용"],
    ["병원·약국", "위치와 시설 정보", "시설명·유형·주소·좌표·진료과목", "후보 검색과 거리 계산"],
    ["날씨", "기온과 강수 상태", "기온·강수량·날씨 상태", "이동 부담 점수"],
    ["대기질", "미세먼지 상태", "PM10·PM2.5·등급", "실외 이동 부담 점수"],
    ["인구", "인구와 고령 인구", "지역·인구·고령 인구", "지역 의료 접근성 분석"],
]
story.append(styled_table(data_tbl,[24*mm,40*mm,61*mm,45*mm]))
story += [Spacer(1,5*mm), ScoreChart(), Spacer(1,3*mm)]
story.append(info_box("최종 점수", "거리 점수 × 0.45 + 날씨 점수 × 0.20 + 대기질 점수 × 0.20 + 사용자 적합도 × 0.15", SKY, BLUE))
story += [Spacer(1,5*mm), P("추천 처리 단계", "KH2")]
process = [
    ["1", "거리 계산", "기준 위치와 시설 사이의 직선거리를 Haversine 공식으로 계산"],
    ["2", "구성 점수화", "각 조건을 정의된 구간에 따라 0~100점으로 변환"],
    ["3", "가중합 계산", "구성 점수에 가중치를 적용하고 소수점 첫째 자리로 반올림"],
    ["4", "TOP 5 선정", "최종 점수를 내림차순으로 정렬"],
    ["5", "이유 생성", "실제로 적용된 중요 조건에서 추천 이유 2~3개 생성"],
]
story.append(styled_table([["단계","처리","내용"]]+process,[15*mm,35*mm,120*mm]))
story.append(PageBreak())

# 4 UX
story += section_title("04", "서비스 구성과 디자인", "추천 결과를 가장 먼저 이해하고 근거를 자연스럽게 확인하는 화면 경험")
nav = [
    ["화면", "목적", "핵심 구성"],
    ["의료기관 추천", "조건 입력과 TOP 5 확인", "검색 조건 · 환경 카드 · 결과 카드 · 지도 · 안내"],
    ["지역 의료 현황", "지역 단위 접근성 파악", "인구·시설 요약 · 인구 대비 지표 · 핵심 해석"],
    ["추천 기준 안내", "결과 산출 방식 공개", "가중치 · 처리 흐름 · 데이터 출처 · 서비스 한계"],
]
story.append(styled_table(nav,[36*mm,52*mm,82*mm]))
story += [Spacer(1,5*mm), P("추천 화면의 정보 우선순위", "KH2")]
priority = [
    ["우선순위", "영역", "표현 원칙"],
    ["1", "추천 TOP 5", "첫 번째 결과를 강조하고 점수 옆에 추천 이유를 배치"],
    ["2", "검색 조건과 환경", "선택 조건과 적용 환경을 짧은 카드로 요약"],
    ["3", "추천 지도", "카드와 동일한 순위·시설·선택 상태를 사용"],
    ["4", "점수 상세", "구성 점수와 가중치를 필요할 때 펼쳐서 확인"],
    ["5", "출처와 한계", "결과 주변과 화면 하단에서 항상 확인 가능"],
]
story.append(styled_table(priority,[22*mm,45*mm,103*mm]))
story += [Spacer(1,5*mm), P("디자인 시스템", "KH2")]
design = [
    ["항목", "방향", "적용 규칙"],
    ["시각 인상", "신뢰감 · 명료함 · 생활 밀착", "전문성을 유지하되 공공 생활 서비스처럼 친근하게 표현"],
    ["색상", "파랑/청록 중심", "좋음·주의·나쁨은 텍스트와 아이콘을 함께 사용"],
    ["타이포그래피", "명확한 정보 위계", "시설명과 핵심 수치는 크게, 설명은 짧은 문장으로 구성"],
    ["컴포넌트", "상태가 드러나는 공통 규칙", "입력·버튼·카드·마커·안내 메시지의 상태를 통일"],
]
story.append(styled_table(design,[31*mm,49*mm,90*mm]))
story.append(PageBreak())

# 5 Functionality
story += section_title("05", "주요 기능과 상호작용", "목록, 지도, 점수 근거가 서로 분리되지 않는 일관된 결과 경험")
functions = [
    ["기능", "사용자 행동", "시스템 처리", "화면 피드백"],
    ["추천 실행", "조건 선택 후 실행", "검증·필터링·점수·정렬·이유 생성", "처리 상태 후 결과 영역 표시"],
    ["카드 선택", "추천 시설 선택", "활성 시설 상태 저장", "대응 지도 마커와 팝업 강조"],
    ["마커 선택", "지도에서 시설 선택", "추천 목록의 시설 탐색", "대응 추천 카드 강조"],
    ["점수 상세", "상세 보기 열기", "구성 점수와 가중치 조회", "최종 점수의 계산 근거 표시"],
    ["조건 변경", "입력값 수정", "기존 결과의 조건 불일치 판별", "재실행 또는 자동 갱신 안내"],
]
story.append(styled_table(functions,[27*mm,35*mm,60*mm,48*mm]))
story += [Spacer(1,6*mm), P("상태별 처리", "KH2")]
states = [
    ["상태", "표현 및 대응"],
    ["초기", "서비스 사용법과 입력 안내를 표시하고 결과 영역에 예시 제공"],
    ["로딩", "추천 계산 중임을 표시하고 중복 실행 방지"],
    ["성공", "조건 요약, TOP 5, 지도, 추천 이유 표시"],
    ["결과 없음", "지역 또는 시설 유형 변경 방법 안내"],
    ["일부 데이터 누락", "정보 없음으로 표시하고 임의 추정 금지"],
    ["데이터 오류", "저장된 대체 데이터 사용 여부와 오류 안내"],
    ["계산 오류", "입력 조건을 유지하고 다시 실행할 수 있게 처리"],
]
story.append(styled_table(states,[34*mm,136*mm]))
story += [Spacer(1,6*mm), P("반응형·접근성 원칙", "KH2"), bullets([
    "좁은 화면에서는 검색 조건, 추천 카드, 지도 순서로 한 열에 배치한다.",
    "색상 외에 텍스트, 아이콘, 순위 번호로 상태와 등급을 구분한다.",
    "모든 입력에 라벨을 제공하고 주요 기능을 키보드로 사용할 수 있게 한다.",
    "차트에는 제목, 단위, 범례, 해석 문장을 함께 제공한다."
])]
story.append(PageBreak())

# 6 Tasks
story += section_title("06", "구현 과업", "의존 관계에 따라 산출물과 완료 조건을 검증하는 작업 중심 개발")
tasks = [
    ["과업", "주요 작업", "산출물", "완료 기준"],
    ["범위·시나리오", "지역과 사용자 시나리오 정의", "시나리오 3종·화면 흐름", "입력·기대 결과·확인 항목 정의"],
    ["데이터 준비", "수집·정제·결측·중복·좌표 검증", "정제 CSV 4종·출처 문서", "앱 로딩과 지도 위치 정상"],
    ["추천 모델", "거리·구성 점수·가중합·이유 생성", "계산 함수·TOP 5", "조건 변화가 순위와 이유에 반영"],
    ["화면 구현", "입력·상태 카드·결과·지도·차트", "추천·분석·안내 화면", "전체 검색 흐름 정상 작동"],
    ["경험 설계", "디자인 시스템·연동·상태·접근성", "공통 UI와 반응형 화면", "설명 없이 핵심 흐름 사용 가능"],
    ["분석·설명", "인구 지표·결과 해석·질의응답", "분석 지표·설명 자료", "핵심 질문과 결론 연결"],
    ["통합 검증", "점수·지도·차트·예외·오프라인", "검증 결과·실행 패키지", "대표 시나리오와 대체 경로 정상"],
]
story.append(styled_table(tasks,[27*mm,54*mm,43*mm,46*mm]))
story += [Spacer(1,6*mm), P("구현 우선순위", "KH2"), bullets([
    "핵심 데이터 로딩과 추천 계산을 먼저 완성한다.",
    "추천 카드와 지도에 동일한 결과 데이터를 연결한다.",
    "핵심 흐름이 안정된 후 시각적 완성도와 부가 분석을 확장한다.",
    "데이터 또는 점수 규칙 변경 시 결과 화면, 차트, 설명 자료를 함께 갱신한다."
]), Spacer(1,5*mm)]
story.append(info_box("기술 구현 방향", "Streamlit을 서비스 셸로 사용하고 pandas로 데이터 처리, folium 또는 pydeck으로 지도, Plotly로 지역 분석 차트를 구현한다. 추천 로직은 화면 코드와 분리해 검산과 재사용이 가능한 함수 단위로 구성한다.", MINT, TEAL))
story.append(PageBreak())

# 7 Validation
story += section_title("07", "검증과 품질 기준", "기능 작동 여부뿐 아니라 계산 근거와 화면 간 일치성을 확인")
checks = [
    ["검증 영역", "확인 내용", "통과 기준"],
    ["데이터", "필수 컬럼·타입·결측·중복·좌표", "모든 파일이 오류 없이 로딩되고 지도 위치가 유효"],
    ["거리", "표본 시설을 별도 계산 또는 외부 지도와 비교", "정의된 허용 오차 안에서 일치"],
    ["점수", "시설 3개 이상을 수작업 검산", "산식과 반올림 규칙에 일치"],
    ["결과", "카드와 지도 TOP 5 비교", "시설·점수·순위가 모두 일치"],
    ["추천 이유", "표시 문구와 실제 조건 비교", "모든 이유가 데이터와 규칙으로 설명 가능"],
    ["지역 차트", "시설 합계와 인구 대비 지표 검산", "별도 집계 값과 일치"],
    ["예외 상태", "결과 없음·누락·데이터 오류·계산 오류", "중단 없이 원인과 해결 행동 안내"],
    ["대체 실행", "외부 연결 없이 전체 흐름 실행", "검색·추천·지도·차트 모두 작동"],
]
story.append(styled_table(checks,[29*mm,73*mm,68*mm]))
story += [Spacer(1,6*mm), P("최종 승인 기준", "KH2"), bullets([
    "대표 사용자 시나리오 3종과 모든 예외 상태가 오류 없이 처리된다.",
    "모든 최종 점수는 0~100 범위이며 동일 입력은 동일 결과를 만든다.",
    "TOP 5마다 추천 이유가 2개 이상 제공되고 점수 조건과 일치한다.",
    "추천 카드, 지도 마커, 점수 상세, 지역 차트의 값이 서로 일치한다.",
    "넓은 화면과 좁은 화면에서 핵심 정보가 잘리거나 겹치지 않는다.",
    "데이터 출처, 계산 방식, 서비스 범위와 한계를 사용자가 확인할 수 있다.",
    "외부 연결 장애에도 저장된 데이터와 대체 자료로 핵심 결과를 전달할 수 있다."
])]
story.append(PageBreak())

# 8 Expected outcomes
story += section_title("08", "기대 효과와 확장 방향", "프로토타입의 가치를 명확히 전달하면서 향후 발전 가능성을 열어 둔다")
effects = [
    ["대상", "기대 효과"],
    ["사용자", "거리 외의 환경 조건과 개인 특성을 함께 고려해 의료기관을 비교할 수 있다."],
    ["서비스 관점", "추천 결과와 근거를 함께 제공하여 블랙박스형 추천보다 이해하기 쉽다."],
    ["데이터 활용", "분리된 공공데이터를 생활 의사결정에 활용하는 구체적 사례를 제시한다."],
    ["지역 분석", "인구 대비 의료기관 지표로 지역 의료 인프라의 상대적 특징을 파악한다."],
    ["개발 관점", "추천 로직과 UI를 분리해 데이터와 규칙을 확장하기 쉬운 구조를 확보한다."],
]
story.append(styled_table(effects,[37*mm,133*mm]))
story += [Spacer(1,7*mm), P("확장 가능성", "KH2")]
extensions = [
    ["확장 항목", "발전 방향"],
    ["이동 경로", "직선거리를 보행·차량·대중교통 실제 경로와 이동 시간으로 대체"],
    ["운영 정보", "의료기관 운영 여부, 진료시간, 휴일 정보 연결"],
    ["사용자 맞춤", "이동 수단, 보행 어려움, 선호 거리 등 개인 조건 추가"],
    ["추천 모델", "사용자 피드백과 검증 데이터에 기반한 가중치 조정"],
    ["지역 확대", "여러 시·군·구 비교와 의료 접근 취약 지역 탐색"],
]
story.append(styled_table(extensions,[43*mm,127*mm]))
story += [Spacer(1,10*mm)]
story.append(Table([[P("결론", "KWhiteBold")], [P("메디웨이는 의료기관의 위치를 보여주는 검색 도구를 넘어, 사용자의 특성과 이동 환경을 함께 해석하는 생활 의료 접근성 의사결정 도구를 제안한다. 핵심은 높은 점수 자체가 아니라 왜 이 시설이 현재 조건에서 더 적합한지를 사용자가 이해할 수 있도록 만드는 데 있다.", "KWhite")]],
                   colWidths=[170*mm], style=TableStyle([
                       ("BACKGROUND",(0,0),(-1,-1),NAVY),("LINEBEFORE",(0,0),(0,-1),5,TEAL),
                       ("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),
                       ("TOPPADDING",(0,0),(-1,-1),9),("BOTTOMPADDING",(0,0),(-1,-1),9)])))

doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
print(OUT)
