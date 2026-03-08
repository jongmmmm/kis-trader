let _currentAlertId = null;

const evtSource = new EventSource("/api/auction/stream");
evtSource.onmessage = function(e) {
  showAuctionPopup(JSON.parse(e.data));
};

function showAuctionPopup(data) {
  _currentAlertId = data.id;

  // 종목 정보
  document.getElementById("au-name").textContent = data.stock_name || "-";
  document.getElementById("au-code").textContent = "(" + data.stock_code + ")";
  document.getElementById("au-price").textContent = Number(data.suggested_price).toLocaleString();
  document.getElementById("au-qty-info").textContent = data.suggested_qty + "주";

  // AI 추천 액션
  const actionEl = document.getElementById("au-action");
  if (data.suggested_action === "buy") {
    actionEl.textContent = "AI 매수 추천";
    actionEl.className = "badge fs-6 px-3 py-2 bg-primary";
  } else if (data.suggested_action === "sell") {
    actionEl.textContent = "AI 매도 추천";
    actionEl.className = "badge fs-6 px-3 py-2 bg-danger";
  } else {
    actionEl.textContent = "AI 관망 추천";
    actionEl.className = "badge fs-6 px-3 py-2 bg-secondary";
  }

  // 신뢰도 바
  const conf = data.ai_confidence || 0;
  const confBar = document.getElementById("au-confidence-bar");
  confBar.style.width = conf + "%";
  confBar.className = "progress-bar " +
    (conf >= 70 ? "bg-success" : conf >= 40 ? "bg-warning" : "bg-danger");
  document.getElementById("au-confidence-val").textContent = conf + "%";

  // 종합 점수
  const score = data.ai_score || 0;
  const scoreEl = document.getElementById("au-score");
  scoreEl.textContent = (score > 0 ? "+" : "") + score.toFixed(1);
  scoreEl.style.color = score > 0 ? "#e74c3c" : score < 0 ? "#3498db" : "#666";

  // 판단 박스 색상
  const verdictBox = document.getElementById("au-verdict-box");
  if (data.suggested_action === "buy") {
    verdictBox.style.background = "#fff5f5";
  } else if (data.suggested_action === "sell") {
    verdictBox.style.background = "#f0f5ff";
  } else {
    verdictBox.style.background = "#f8f9fa";
  }

  // 팩터 테이블
  const factorsTbody = document.getElementById("au-factors");
  factorsTbody.innerHTML = "";
  const factors = data.ai_factors || [];
  factors.forEach(function(f) {
    const tr = document.createElement("tr");
    const scoreColor = f.score > 10 ? "#e74c3c" : f.score < -10 ? "#3498db" : "#888";
    const scoreIcon = f.score > 10 ? "\u25B2" : f.score < -10 ? "\u25BC" : "\u25CF";
    tr.innerHTML =
      '<td class="fw-bold">' + f.name + '</td>' +
      '<td class="text-center fw-bold" style="color:' + scoreColor + '">' +
        scoreIcon + ' ' + (f.score > 0 ? "+" : "") + f.score + '</td>' +
      '<td class="text-muted">' + (f.reason || "-") + '</td>';
    factorsTbody.appendChild(tr);
  });

  // AI 요약
  document.getElementById("au-summary").textContent = data.ai_summary || "분석 데이터 없음";

  // 만료 시간
  document.getElementById("au-expires").textContent = data.expires_at.replace("T", " ").slice(0, 19);

  // 팝업 표시
  document.getElementById("auction-overlay").classList.add("show");
}

function auctionDecide(decision) {
  if (!_currentAlertId) return;
  if (decision === "pass") {
    document.getElementById("auction-overlay").classList.remove("show");
    var passedId = _currentAlertId;
    _currentAlertId = null;
    fetch("/api/auction/decide/" + passedId, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision: "pass" }),
    });
    return;
  }
  fetch("/api/auction/decide/" + _currentAlertId, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision: decision }),
  })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      document.getElementById("auction-overlay").classList.remove("show");
      _currentAlertId = null;
      if (d.message) alert(d.message);
    })
    .catch(function() { alert("처리 실패"); });
}

// 페이지 로드 시 미결 알림 확인
fetch("/api/auction/pending")
  .then(function(r) { return r.json(); })
  .then(function(list) { if (list.length > 0) showAuctionPopup(list[0]); });
