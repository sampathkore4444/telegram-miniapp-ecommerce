// Login / onboarding view.
import { isTelegramAvailable, loginWithTelegram, loginDemo } from "../auth.js";
import { navigate } from "../router.js";
import { el, toast } from "../ui.js";
import { t } from "../i18n.js";

export async function renderLogin(root) {
  root.innerHTML = "";
  const host = el(`
    <div class="container">
      <div class="login-hero">
        <div class="login-logo">&#128722;</div>
        <h1>Telegram Shop</h1>
        <p class="muted">${t("login.subtitle")}</p>
      </div>
      <div class="card" style="padding:18px">
        ${isTelegramAvailable()
          ? `<button class="btn btn-primary" id="tg-login">${t("login.continue_tg")}</button>`
          : `<p class="muted center small" style="margin-bottom:14px">${t("login.outside")}</p>
             <button class="btn btn-primary" id="demo-buyer">${t("login.demo_buyer")}</button>
             <div style="height:10px"></div>
             <button class="btn btn-outline" id="demo-admin">${t("login.demo_admin")}</button>`}
      </div>
      <p class="small muted center" style="margin-top:16px">${t("login.terms")}</p>
    </div>`);

  host.querySelector("#tg-login")?.addEventListener("click", async () => {
    try {
      await loginWithTelegram();
      navigate("");
    } catch (err) {
      toast(err.message, "error");
    }
  });
  host.querySelector("#demo-buyer")?.addEventListener("click", async () => {
    await loginDemo("buyer");
    navigate("");
  });
  host.querySelector("#demo-admin")?.addEventListener("click", async () => {
    await loginDemo("admin");
    navigate("");
  });

  root.appendChild(host);
}
