// Etermory — JavaScript só para interações: curtir sem recarregar,
// tema claro/escuro, limite de 3 emoções e confirmações.
(function () {
  "use strict";

  const tokenCsrf = document.querySelector('meta[name="csrf-token"]')?.content;

  // ---------- Curtir sem recarregar (RF20) ----------
  document.addEventListener("submit", async function (evento) {
    const form = evento.target;
    if (!form.matches("[data-curtir]")) return;
    evento.preventDefault();
    const botao = form.querySelector("button");
    botao.disabled = true;
    try {
      const resposta = await fetch(form.action, {
        method: "POST",
        headers: { "X-CSRFToken": tokenCsrf, Accept: "application/json" },
        credentials: "same-origin",
      });
      if (!resposta.ok) throw new Error("Falha ao curtir");
      const dados = await resposta.json();
      botao.classList.toggle("curtido", dados.curtiu);
      botao.setAttribute("aria-pressed", String(dados.curtiu));
      botao.querySelector("[data-total]").textContent = dados.total;
    } catch (erro) {
      form.submit(); // sem JS funcionando, envia o formulário normal
    } finally {
      botao.disabled = false;
    }
  });

  // ---------- Confirmação antes de ações destrutivas ----------
  document.addEventListener("submit", function (evento) {
    const mensagem = evento.target.dataset?.confirmar;
    if (mensagem && !window.confirm(mensagem)) evento.preventDefault();
  }, true);

  // ---------- Tema claro/escuro ----------
  document.querySelectorAll("[data-alternar-tema]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      const raiz = document.documentElement;
      const escuroAgora = raiz.dataset.theme
        ? raiz.dataset.theme === "dark"
        : window.matchMedia("(prefers-color-scheme: dark)").matches;
      raiz.dataset.theme = escuroAgora ? "light" : "dark";
      try { localStorage.setItem("etermory-tema", raiz.dataset.theme); } catch (e) {}
    });
  });

  // ---------- No máximo 3 emoções (RN11 na tela) ----------
  document.querySelectorAll("fieldset[data-limite]").forEach(function (grupo) {
    const limite = Number(grupo.dataset.limite);
    const caixas = grupo.querySelectorAll('input[type="checkbox"]');
    function atualizar() {
      const marcadas = grupo.querySelectorAll('input[type="checkbox"]:checked').length;
      caixas.forEach(function (caixa) {
        caixa.disabled = !caixa.checked && marcadas >= limite;
      });
    }
    caixas.forEach(function (caixa) { caixa.addEventListener("change", atualizar); });
    atualizar();
  });
})();
