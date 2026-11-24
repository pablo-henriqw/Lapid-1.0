document.addEventListener("click", function (e) {
  var btn = e.target.closest("[data-copy]");
  if (!btn) return;
  var code = btn.parentElement.querySelector("code");
  if (!code || !navigator.clipboard) return;
  navigator.clipboard.writeText(code.textContent).then(function () {
    var old = btn.textContent;
    btn.textContent = "Copiado";
    setTimeout(function () { btn.textContent = old; }, 1600);
  });
});
