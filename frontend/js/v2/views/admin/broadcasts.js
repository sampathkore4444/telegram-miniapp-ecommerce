import { api } from "../../api.js";
import { el, esc, toast } from "../../ui.js";

export async function renderBroadcasts(root) {
  root.innerHTML = "";
  const host = el(`
    <div class="container">
      <h1 class="title">Broadcast</h1>
      <div class="card">
        <div class="field">
          <label>Message to your customers</label>
          <textarea class="input" id="msg" placeholder="Write a message to every buyer who has ordered from this store…" maxlength="4000"></textarea>
        </div>
        <div class="small muted" style="margin-bottom:12px"><span id="count">0</span> / 4000 characters</div>
        <button class="btn btn-primary" id="send">Send broadcast</button>
      </div>
      <p class="small muted" style="margin-top:4px">Only buyers who have ordered from this store receive the message. Admins are never included.</p>
      <div id="result"></div>
    </div>`);

  const msg = host.querySelector("#msg");
  msg.addEventListener("input", () => {
    host.querySelector("#count").textContent = msg.value.length;
  });

  host.querySelector("#send").addEventListener("click", async () => {
    const text = msg.value.trim();
    if (!text) return toast("Enter a message first", "error");
    const btn = host.querySelector("#send");
    btn.disabled = true;
    btn.textContent = "Sending…";
    const result = host.querySelector("#result");
    result.innerHTML = "";
    try {
      const res = await api.post("/api/admin/broadcasts", { message: text });
      result.appendChild(el(`
        <div class="card" style="background:var(--green-bg)">
          <div class="row">
            <span style="font-weight:700;color:var(--green)">Broadcast sent</span>
          </div>
          <div class="small muted" style="margin-top:4px">${res.sent} delivered · ${res.skipped} skipped of ${res.total} buyers${res.admin_recipients ? ` (${res.admin_recipients} admin excluded)` : ""}</div>
        </div>`));
      toast("Broadcast sent", "success");
    } catch (err) {
      toast(err.message, "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "Send broadcast";
    }
  });

  root.appendChild(host);
}
