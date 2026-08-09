import { api } from "../../api.js";
import { el, esc, toast, confirmBox } from "../../ui.js";

const STARS = (n) =>
  `<span style="color:var(--star,#f6b73c);letter-spacing:1px">${"★".repeat(n)}${"☆".repeat(5 - n)}</span>`;

export async function renderReviews(root) {
  root.innerHTML = "";
  let state = { page: 1, pageSize: 50, status: "all" };

  const host = el(`
    <div class="container">
      <h1 class="title">Reviews</h1>
      <div class="pill-tabs">
        <button class="pill active" data-s="all">All</button>
        <button class="pill" data-s="approved">Approved</button>
        <button class="pill" data-s="hidden">Hidden</button>
      </div>
      <div id="list"></div>
    </div>`);

  const list = host.querySelector("#list");

  const load = async () => {
    list.innerHTML = `<div class="skeleton" style="height:120px"></div>`;
    const params = new URLSearchParams({ page: state.page, page_size: state.pageSize, status: state.status });
    const data = await api.get(`/api/admin/reviews?${params}`);
    list.innerHTML = "";
    if (data.items.length === 0) {
      list.appendChild(el(`<div class="empty"><span class="ico">&#11088;</span>No reviews here yet.</div>`));
      return;
    }
    for (const r of data.items) {
      const row = el(`
        <div class="card">
          <div class="row">
            <div class="grow" style="min-width:0">
              <div class="row">
                <b style="font-size:14px">${esc(r.product_name || `Product #${r.product_id}`)}</b>
                ${r.is_approved ? `<span class="badge badge-completed">approved</span>` : `<span class="badge badge-cancelled">hidden</span>`}
              </div>
              <div class="small">${STARS(r.rating)} <span class="muted">· ${esc(r.user_name)} · ${esc(r.created_at || "")}</span></div>
              ${r.comment ? `<p class="muted" style="font-size:14px;margin-top:6px;white-space:pre-wrap">${esc(r.comment)}</p>` : ""}
              ${r.images && r.images.length ? `<div class="row" style="margin-top:6px;gap:6px">${r.images.slice(0, 4).map((src) => `<img src="${esc(src)}" style="width:52px;height:52px;border-radius:8px;object-fit:cover" data-err="remove">`).join("")}</div>` : ""}
            </div>
            <div class="btn-row" style="margin:0;align-self:flex-start">
              <button class="btn btn-sm btn-outline" data-toggle>${r.is_approved ? "Hide" : "Approve"}</button>
              <button class="btn btn-sm btn-danger" data-del>Delete</button>
            </div>
          </div>
        </div>`);
      row.querySelector("[data-toggle]").addEventListener("click", async () => {
        try {
          await api.patch(`/api/admin/reviews/${r.id}`, { is_approved: !r.is_approved });
          toast(r.is_approved ? "Review hidden" : "Review approved", "success");
          load();
        } catch (err) {
          toast(err.message, "error");
        }
      });
      row.querySelector("[data-del]").addEventListener("click", async () => {
        const ok = await confirmBox("Delete this review permanently?", "Delete review");
        if (!ok) return;
        try {
          await api.del(`/api/admin/reviews/${r.id}`);
          toast("Deleted", "success");
          load();
        } catch (err) {
          toast(err.message, "error");
        }
      });
      list.appendChild(row);
    }
  };

  host.querySelectorAll(".pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      state.status = pill.dataset.s;
      state.page = 1;
      host.querySelectorAll(".pill").forEach((p) => p.classList.toggle("active", p === pill));
      load();
    });
  });

  root.appendChild(host);
  await load();
}
