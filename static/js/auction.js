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

  // 원형 게이지 (종합점수: -100 ~ +100 → 0~100%)
  const score = data.ai_score || 0;
  const scoreEl = document.getElementById("au-score");
  scoreEl.textContent = (score > 0 ? "+" : "") + score.toFixed(1);
  const scoreAbs = Math.min(Math.abs(score), 100);
  const gaugeCircle = document.getElementById("au-gauge-circle");
  const circumference = 327; // 2 * PI * 52
  const gaugeOffset = circumference - (circumference * scoreAbs / 100);
  gaugeCircle.style.strokeDashoffset = gaugeOffset;
  if (score > 15) {
    gaugeCircle.style.stroke = "#e74c3c";
    scoreEl.style.color = "#e74c3c";
  } else if (score < -15) {
    gaugeCircle.style.stroke = "#3498db";
    scoreEl.style.color = "#3498db";
  } else {
    gaugeCircle.style.stroke = "#f39c12";
    scoreEl.style.color = "#f39c12";
  }

  // 신뢰도 바
  const conf = data.ai_confidence || 0;
  const confBar = document.getElementById("au-confidence-bar");
  confBar.style.width = conf + "%";
  confBar.style.background = conf >= 70 ? "#27ae60" : conf >= 40 ? "#f39c12" : "#e74c3c";
  document.getElementById("au-confidence-val").textContent = conf + "%";

  // 판단 설명
  const verdictText = document.getElementById("au-verdict-text");
  const posCount = (data.ai_factors || []).filter(f => f.score > 5).length;
  const negCount = (data.ai_factors || []).filter(f => f.score < -5).length;
  verdictText.textContent = "긍정 " + posCount + "개 / 부정 " + negCount + "개 신호 감지";

  // 판단 박스 색상
  const verdictBox = document.getElementById("au-verdict-box");
  if (data.suggested_action === "buy") {
    verdictBox.style.background = "#fff5f5";
  } else if (data.suggested_action === "sell") {
    verdictBox.style.background = "#f0f5ff";
  } else {
    verdictBox.style.background = "#f8f9fa";
  }

  // 팩터 수평 바 차트
  const factorsDiv = document.getElementById("au-factors");
  factorsDiv.innerHTML = "";
  const factors = data.ai_factors || [];
  const maxScore = Math.max(...factors.map(f => Math.abs(f.score)), 30);

  factors.forEach(function(f) {
    const pct = Math.min(Math.abs(f.score) / maxScore * 100, 100);
    const isPositive = f.score > 0;
    const barColor = f.score > 10 ? "#e74c3c" : f.score < -10 ? "#3498db" : "#adb5bd";
    const emoji = f.score > 10 ? "🔴" : f.score < -10 ? "🔵" : "⚪";

    const row = document.createElement("div");
    row.style.cssText = "display:flex;align-items:center;gap:8px;";
    row.innerHTML =
      '<div style="width:70px;font-size:11px;font-weight:700;text-align:right;flex-shrink:0;color:#444;">' + f.name + '</div>' +
      '<div style="flex:1;height:20px;background:#f1f3f5;border-radius:10px;overflow:hidden;position:relative;">' +
        // 중앙선
        '<div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:#ccc;z-index:1;"></div>' +
        // 바
        (isPositive
          ? '<div style="position:absolute;left:50%;top:2px;bottom:2px;width:' + (pct/2) + '%;background:' + barColor + ';border-radius:0 8px 8px 0;transition:width 0.8s ease;"></div>'
          : '<div style="position:absolute;right:50%;top:2px;bottom:2px;width:' + (pct/2) + '%;background:' + barColor + ';border-radius:8px 0 0 8px;transition:width 0.8s ease;"></div>'
        ) +
      '</div>' +
      '<div style="width:40px;font-size:11px;font-weight:700;color:' + barColor + ';text-align:right;">' +
        (f.score > 0 ? "+" : "") + f.score +
      '</div>';

    // 근거 툴팁 (호버 시 표시)
    const tooltip = document.createElement("div");
    tooltip.style.cssText = "font-size:10px;color:#888;padding-left:78px;margin-top:-2px;display:none;";
    tooltip.textContent = f.reason || "";
    row.addEventListener("mouseenter", function() { tooltip.style.display = "block"; });
    row.addEventListener("mouseleave", function() { tooltip.style.display = "none"; });

    factorsDiv.appendChild(row);
    factorsDiv.appendChild(tooltip);
  });

  // AI 요약
  document.getElementById("au-summary").textContent = data.ai_summary || "분석 데이터 없음";

  // 만료 시간
  document.getElementById("au-expires").textContent = data.expires_at.replace("T", " ").slice(0, 19);

  // 팝업 표시
  document.getElementById("auction-overlay").classList.add("show");
}

// ─── 주문 설정 모달 ───
var _orderDecision = null;

function openOrderModal(decision) {
  _orderDecision = decision;
  var overlay = document.getElementById("order-overlay");
  var title = document.getElementById("order-config-title");
  var confirmBtn = document.getElementById("order-confirm-btn");
  var priceInput = document.getElementById("order-price-input");
  var qtyInput = document.getElementById("order-qty-input");
  var typeSelect = document.getElementById("order-type-select");
  var stockInfo = document.getElementById("order-stock-info");

  // 종목 정보 표시
  var stockName = document.getElementById("au-name").textContent;
  var stockCode = document.getElementById("au-code").textContent;
  stockInfo.textContent = stockName + " " + stockCode;

  // AI 추천 가격/수량 세팅
  var suggestedPrice = document.getElementById("au-price").textContent.replace(/,/g, "");
  var suggestedQty = document.getElementById("au-qty-info").textContent.replace("주", "");
  priceInput.value = parseInt(suggestedPrice) || 0;
  priceInput.disabled = false;
  qtyInput.value = parseInt(suggestedQty) || 1;
  typeSelect.value = "limit";

  if (decision === "buy") {
    title.innerHTML = '<i class="fa-solid fa-arrow-up me-2"></i>매수 주문';
    title.style.color = "#0d6efd";
    confirmBtn.className = "btn btn-primary flex-fill py-2 fw-bold";
  } else {
    title.innerHTML = '<i class="fa-solid fa-arrow-down me-2"></i>매도 주문';
    title.style.color = "#dc3545";
    confirmBtn.className = "btn btn-danger flex-fill py-2 fw-bold";
  }

  updateOrderTotal();
  // AI 분석 팝업 숨기고 주문 모달 표시
  document.getElementById("auction-overlay").classList.remove("show");
  overlay.style.display = "flex";
}

function closeOrderModal() {
  document.getElementById("order-overlay").style.display = "none";
  _orderDecision = null;
  // AI 분석 팝업 다시 표시
  document.getElementById("auction-overlay").classList.add("show");
}

function updateOrderTotal() {
  var price = parseInt(document.getElementById("order-price-input").value) || 0;
  var qty = parseInt(document.getElementById("order-qty-input").value) || 0;
  document.getElementById("order-total").textContent = (price * qty).toLocaleString();
}

// 입력 변경 시 예상 금액 업데이트
document.addEventListener("DOMContentLoaded", function() {
  var priceInput = document.getElementById("order-price-input");
  var qtyInput = document.getElementById("order-qty-input");
  var typeSelect = document.getElementById("order-type-select");
  if (priceInput) priceInput.addEventListener("input", updateOrderTotal);
  if (qtyInput) qtyInput.addEventListener("input", updateOrderTotal);
  if (typeSelect) typeSelect.addEventListener("change", function() {
    var priceInput = document.getElementById("order-price-input");
    if (this.value === "market") {
      priceInput.value = 0;
      priceInput.disabled = true;
    } else {
      priceInput.disabled = false;
      var suggestedPrice = document.getElementById("au-price").textContent.replace(/,/g, "");
      priceInput.value = parseInt(suggestedPrice) || 0;
    }
    updateOrderTotal();
  });
});

function confirmOrder() {
  if (!_currentAlertId || !_orderDecision) return;
  var price = parseInt(document.getElementById("order-price-input").value) || 0;
  var qty = parseInt(document.getElementById("order-qty-input").value) || 0;
  var orderType = document.getElementById("order-type-select").value;

  if (qty <= 0) { alert("수량을 입력해주세요."); return; }
  if (orderType === "limit" && price <= 0) { alert("가격을 입력해주세요."); return; }

  var label = _orderDecision === "buy" ? "매수" : "매도";
  var priceText = orderType === "market" ? "시장가" : price.toLocaleString() + "원";
  if (!confirm(label + " 주문을 실행합니다.\n\n" + priceText + " × " + qty + "주 = " + (price * qty).toLocaleString() + "원\n\n진행하시겠습니까?")) return;

  fetch("/api/auction/decide/" + _currentAlertId, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      decision: _orderDecision,
      price: price,
      quantity: qty,
    }),
  })
    .then(function(r) { return r.json(); })
    .then(function(d) {
      document.getElementById("auction-overlay").classList.remove("show");
      document.getElementById("order-overlay").style.display = "none";
      _currentAlertId = null;
      _orderDecision = null;
      if (d.message) alert(d.message);
    })
    .catch(function() { alert("주문 처리 실패"); });
}

function auctionDecide(decision) {
  if (!_currentAlertId) return;
  if (decision === "pass") {
    document.getElementById("auction-overlay").classList.remove("show");
    document.getElementById("order-overlay").style.display = "none";
    var passedId = _currentAlertId;
    _currentAlertId = null;
    fetch("/api/auction/decide/" + passedId, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision: "pass" }),
    });
    return;
  }
}

// 페이지 로드 시 미결 알림 확인
fetch("/api/auction/pending")
  .then(function(r) { return r.json(); })
  .then(function(list) { if (list.length > 0) showAuctionPopup(list[0]); });
