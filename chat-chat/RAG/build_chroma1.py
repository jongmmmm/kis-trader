# build_chroma1.py  →  PDF 읽어서 ChromaDB에 저장 (한 번만 실행)
#                       "재료 준비"

# # build_chroma.py
# build_chroma.py 실행
#       ↓
# 1. PDF 읽기 (LlamaParse)
#       ↓
# 2. Markdown으로 변환 → output.md 저장
#       ↓
# 3. 헤더 기준 1차 분할
#       ↓
# 4. 글자수 기준 2차 분할
#       ↓
# 5. 임베딩 (BAAI/bge-m3)
#       ↓
# 6. ChromaDB 저장 완료!
# PDF → Markdown 변환 → 텍스트 분할 → 임베딩 → ChromaDB 저장

# API
#     ↓
# 📦 Document Loader (LlamaParse)
#     → PDF → Markdown 변환
#     → output.md 저장

#     ↓
# ✂️ Text Splitter
#     → 1차: MarkdownHeaderTextSplitter (헤더 기준)
#     → 2차: RecursiveCharacterTextSplitter (글자수 기준)

#     ↓
# 🔢 Embedding (벡터 변환)
#     → HuggingFaceEmbeddings
#     → "BAAI/bge-m3" 모델 사용

#     ↓
# 🗄️ Vector DB 저장
#     → chromadb / langchain-chroma

# -------- 여기까지가 데이터 준비 단계 --------
# ============================================================
# build_chroma1.py
# 역할: PDF 읽어서 ChromaDB에 저장 (최초 1회 또는 PDF 변경 시 실행)
#
# 흐름:
# PDF 파일
#   ↓ LlamaParse (PDF → Markdown)
#   ↓ output.md 저장
#   ↓ MarkdownHeaderTextSplitter (헤더 기준 1차 분할)
#   ↓ RecursiveCharacterTextSplitter (300자 기준 2차 분할)
#   ↓ BAAI/bge-m3 임베딩
#   ↓ ChromaDB 저장 완료!
# ============================================================
# ============================================================
# build_chroma1.py
# 역할: PDF → ChromaDB 저장 (최초 1회 or PDF 변경 시 실행)
# 위치: ohsungjun_chat/RAG/build_chroma1.py
# ============================================================

import os
import certifi
import shutil

os.environ["SSL_CERT_FILE"]      = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

import nest_asyncio
from dotenv import load_dotenv
from llama_cloud_services import LlamaParse
from llama_index.core import SimpleDirectoryReader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

load_dotenv()
nest_asyncio.apply()
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ─────────────────────────────────────────────
# ✅ 경로 설정
# build_chroma1.py 는 RAG/ 폴더 안에 있음
# BASE_DIR = ohsungjun_chat/RAG/
# ─────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))  # RAG/
PDF_DIR     = os.path.join(BASE_DIR, "RAG_PDF")           # RAG/RAG_PDF/
OUTPUT_FILE = os.path.join(PDF_DIR, "output.md")          # RAG/RAG_PDF/output.md
DB_PATH     = os.path.join(BASE_DIR, "chroma_db")         # RAG/chroma_db/

# ─────────────────────────────────────────────
# 1. PDF 파일 목록 수집
# ─────────────────────────────────────────────
pdf_files = [
    os.path.join(PDF_DIR, f)
    for f in os.listdir(PDF_DIR)
    if f.endswith(".pdf")
]

if not pdf_files:
    print("❌ RAG_PDF 폴더에 PDF 파일이 없습니다.")
    exit(1)

print(f"📄 처리할 PDF: {len(pdf_files)}개")
for f in pdf_files:
    print(f"   - {os.path.basename(f)}")

# ─────────────────────────────────────────────
# 2. PDF → Markdown (LlamaParse)
# ─────────────────────────────────────────────
parser = LlamaParse(result_type="markdown", verbose=True, language="ko")
documents = SimpleDirectoryReader(
    input_files=pdf_files,
    file_extractor={".pdf": parser},
).load_data()

# ─────────────────────────────────────────────
# 3. output.md 저장
# ─────────────────────────────────────────────
full_text = "\n\n".join([doc.text for doc in documents])
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(full_text)
print(f"✅ {OUTPUT_FILE} 저장 완료!")

# ─────────────────────────────────────────────
# 4. 헤더 기준 1차 분할
# ─────────────────────────────────────────────
md_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "Header 1")],
    strip_headers=False,
)
md_splits = md_splitter.split_text(full_text)

# ─────────────────────────────────────────────
# 5. 글자수 기준 2차 분할
# ─────────────────────────────────────────────
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=20,
)
split_docs = text_splitter.split_documents(md_splits)

# ─────────────────────────────────────────────
# 6. 임베딩
# ─────────────────────────────────────────────
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

# ─────────────────────────────────────────────
# 7. 기존 DB 초기화 후 새로 저장
# ─────────────────────────────────────────────
if os.path.exists(DB_PATH):
    shutil.rmtree(DB_PATH)
    print("🗑️  기존 ChromaDB 초기화 완료")

db = Chroma.from_documents(
    split_docs,
    embeddings,
    persist_directory=DB_PATH,
    collection_name="my_chatbot",
)

print("✅ ChromaDB 저장 완료!")
print(f"   저장 위치: {DB_PATH}")
print(f"   총 청크 수: {len(split_docs)}")