import { api } from "./api.js";
import { el, toast, modal } from "./ui.js";
import { t } from "./i18n.js";

const LEAFLET_VERSION = "1.9.4";
const FALLBACK = { lat: 12.5657, lng: 104.991 };

let leafletPromise = null;

function loadLeaflet() {
  if (window.L) return Promise.resolve();
  if (leafletPromise) return leafletPromise;
  leafletPromise = new Promise((resolve, reject) => {
    if (!document.getElementById("leaflet-css")) {
      const link = document.createElement("link");
      link.id = "leaflet-css";
      link.rel = "stylesheet";
      link.href = `https://unpkg.com/leaflet@${LEAFLET_VERSION}/dist/leaflet.css`;
      document.head.appendChild(link);
    }
    const script = document.createElement("script");
    script.src = `https://unpkg.com/leaflet@${LEAFLET_VERSION}/dist/leaflet.js`;
    script.onload = () => resolve();
    script.onerror = () => {
      leafletPromise = null;
      reject(new Error(t("geo.map_error")));
    };
    document.head.appendChild(script);
  });
  return leafletPromise;
}

function reverseGeocode(lat, lon) {
  return api.get(`/api/geocode/reverse?lat=${lat}&lon=${lon}`).then((d) => d.address);
}

function openMapPicker(lat, lng, inputEl, setStatus) {
  setStatus(t("geo.adjust"), "info");
  const host = el(`
    <div>
      <p class="small muted" style="margin-bottom:8px">${t("geo.drag_hint")}</p>
      <div id="pick-map" style="width:100%;height:300px;border-radius:14px;overflow:hidden;z-index:0"></div>
      <p class="small geo-status" id="pick-status" hidden></p>
    </div>`);
  const pickStatus = host.querySelector("#pick-status");
  const setPick = (html, kind) => {
    pickStatus.className = `small geo-status${kind ? ` ${kind}` : ""}`;
    pickStatus.innerHTML = html || "";
    pickStatus.hidden = !html;
  };
  let marker = null;
  let map = null;

  modal({
    title: t("geo.choose"),
    body: host,
    okText: t("geo.use_this"),
    onOk: async () => {
      if (!marker) throw new Error(t("geo.loading_map"));
      const pos = marker.getLatLng();
      setPick(t("geo.resolving"), "info");
      try {
        const address = await reverseGeocode(pos.lat, pos.lng);
        inputEl.value = address;
        inputEl.focus();
        setStatus(t("geo.captured"), "ok");
      } catch (err) {
        throw new Error(t("geo.resolve_fail"));
      }
    },
  });

  loadLeaflet()
    .then(() => {
      requestAnimationFrame(() => {
        const mapEl = host.querySelector("#pick-map");
        map = L.map(mapEl, { scrollWheelZoom: false }).setView([lat, lng], 15);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        }).addTo(map);
        marker = L.marker([lat, lng], { draggable: true }).addTo(map);
        marker.on("dragend", () => {
          const p = marker.getLatLng();
          map.setView(p, map.getZoom(), { animate: true });
        });
        map.on("click", (e) => {
          marker.setLatLng(e.latlng);
          map.setView(e.latlng, map.getZoom(), { animate: true });
        });
        setTimeout(() => map.invalidateSize(), 60);
      });
    })
    .catch(() => {
      setPick(t("geo.map_load_fail"), "err");
    });
}

export function attachGeoButton(btn, status, inputEl) {
  const setStatus = (html, kind) => {
    status.className = `small geo-status${kind ? ` ${kind}` : ""}`;
    status.innerHTML = html || "";
    status.hidden = !html;
  };
  btn.addEventListener("click", () => {
    if (!("geolocation" in navigator)) {
      return toast(t("geo.not_supported"), "error");
    }
    btn.disabled = true;
    const origLabel = btn.innerHTML;
    btn.innerHTML = t("geo.locating");
    setStatus(t("geo.getting"), "info");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        btn.disabled = false;
        btn.innerHTML = origLabel;
        openMapPicker(pos.coords.latitude, pos.coords.longitude, inputEl, setStatus);
      },
      () => {
        btn.disabled = false;
        btn.innerHTML = origLabel;
        setStatus(t("geo.manual_pin"), "info");
        openMapPicker(FALLBACK.lat, FALLBACK.lng, inputEl, setStatus);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 }
    );
  });
}
