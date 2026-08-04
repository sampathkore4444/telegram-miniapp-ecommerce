// Login / onboarding view.
import { isTelegramAvailable, loginWithTelegram, loginDemo } from "../auth.js";
import { navigate } from "../router.js";
import { el, toast } from "../ui.js";

export async function renderLogin(root) {
  root.innerHTML = "";
  const host = el(`
    <div class="container">
      <div class="login-hero">
        <div class="login-logo">&#128722;</div>
        <h1>Telegram Shop</h1>
        <p class="muted">Sign in with your Telegram account to start shopping.</p>
      </div>
      <div class="card" style="padding:18px">
        ${isTelegramAvailable()
          ? `<button class="btn btn-primary" id="tg-login">Continue with Telegram</button>`
          : `<p class="muted center small" style="margin-bottom:14px">Running outside Telegram — use a demo account (development mode).</p>
             <button class="btn btn-primary" id="demo-buyer">Demo: Shop as Buyer</button>
             <div style="height:10px"></div>
             <button class="btn btn-outline" id="demo-admin">Demo: Store Owner</button>`}
      </div>
      <p class="small muted center" style="margin-top:16px">By continuing you agree to the store's terms.</p>
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
