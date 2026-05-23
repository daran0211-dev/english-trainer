#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 패키지 확인 및 설치
if ! python3 -c "import streamlit" 2>/dev/null; then
  echo "필요한 패키지를 설치합니다..."
  pip3 install -r requirements.txt -q
fi

# NLTK 데이터 확인 및 다운로드
python3 -c "
import nltk, os
data_path = os.path.expanduser('~/nltk_data')
needed = ['averaged_perceptron_tagger_eng', 'punkt_tab']
for pkg in needed:
    try:
        nltk.data.find(f'tokenizers/{pkg}' if 'punkt' in pkg else f'taggers/{pkg}')
    except LookupError:
        print(f'NLTK 데이터 다운로드: {pkg}')
        nltk.download(pkg, quiet=True)
" 2>/dev/null

# 브라우저 자동 열기 (3초 후)
(sleep 3 && open http://localhost:8502) &

echo "================================================"
echo "  영어 암기 트레이너 시작 중..."
echo "  브라우저: http://localhost:8502"
echo "  종료: Ctrl+C"
echo "================================================"

python3 -m streamlit run app.py --server.port 8502 --server.headless true
