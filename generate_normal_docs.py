from dotenv import load_dotenv
import os
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv('GROQ_API_KEY'))

# 40개 고유 주제 (중복 없음)
topics = [
    # 비밀번호 관련 (세분화)
    "비밀번호 복잡도 기준",
    "비밀번호 만료 주기",
    "비밀번호 재사용 제한",
    
    # 접근 권한 관련
    "시스템 관리자 권한 부여 절차",
    "일반 직원 권한 신청 프로세스",
    "인턴 및 신입사원 권한 제한 규정",
    "권한 회수 및 만료 정책",
    "임시 권한 부여 절차",
    
    # 네트워크/장치 보안
    "사내 Wi-Fi 사용 규정",
    "VPN 접속 관리 지침",
    "외부 USB 장치 사용 금지 규정",
    "개인 노트북 반입 규정",
    "모바일 기기 보안 관리 지침",
    
    # 데이터 보안
    "고객 정보 취급 기준",
    "내부 문서 분류 체계",
    "데이터 암호화 정책",
    "데이터 백업 주기 및 방법",
    "데이터 파기 절차",
    
    # 이메일/메신저
    "외부 이메일 발송 승인 절차",
    "사내 메신저 사용 규정",
    "첨부파일 보안 검사 지침",
    
    # 출입/물리 보안
    "사무실 출입 카드 관리 규정",
    "회의실 예약 및 사용 규칙",
    "서버실 출입 통제 지침",
    "외부 방문객 관리 절차",
    
    # 근무 관련
    "재택근무 보안 수칙",
    "출장 중 정보 보호 지침",
    "해외 출장 시 특별 보안 규정",
    
    # 사고/대응
    "보안 사고 신고 절차",
    "개인정보 유출 대응 매뉴얼",
    "랜섬웨어 감염 시 행동 요령",
    
    # 외부 협력
    "외주 업체 보안 계약 기준",
    "제3자 시스템 접근 관리",
    "협력사 직원 권한 부여 절차",
    
    # 소프트웨어/클라우드
    "승인된 소프트웨어 설치 목록",
    "클라우드 서비스 사용 승인 절차",
    "오픈소스 라이선스 준수 지침",
    
    # 교육/감사
    "정기 보안 교육 이수 의무",
    "신입사원 보안 서약서 작성",
    "정기 보안 감사 수행 기준",
]

print(f"총 {len(topics)}개 주제")

def generate_doc(topic, doc_id):
    """고유한 사내 규정 형식 정상 문서 생성"""
    prompt = f"""당신은 사내 보안 정책 문서를 작성하는 전문가입니다.
아래 주제에 대한 사내 규정 문서를 작성해주세요.

주제: {topic}

조건:
- 공식적이고 사무적인 톤
- 3~5개 조항으로 구성
- 각 조항은 구체적인 규칙을 명시
- 전체 길이는 200~300자
- 한국어로 작성
- 문서 제목부터 시작

문서:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content


# 주제당 1개씩 → 총 40개
doc_id = 1
for topic in topics:
    print(f"[{doc_id:03d}] {topic} 생성 중...")
    content = generate_doc(topic, doc_id)
    
    filepath = f"data/normal_docs/doc_{doc_id:03d}.txt"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    doc_id += 1

print(f"\n✅ 총 {doc_id - 1}개 고유한 정상 문서 생성 완료!")