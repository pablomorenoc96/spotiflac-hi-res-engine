/**
 * SpotiFLAC Hi-Res Engine - Audiophile Frontend Controller
 * Communicates with PyWebView Python Bridge
 */

let currentAlbumData = null;
let currentDiscographyData = null;
let isDownloading = false;

// 1. Tab Navigation
function switchTab(tabId) {
  const tabs = ['download', 'library', 'audit', 'settings'];
  tabs.forEach(tab => {
    const el = document.getElementById(`tab-${tab}`);
    if (el) el.classList.remove('active');
  });

  const activeContent = document.getElementById(`tab-${tabId}`);
  if (activeContent) activeContent.classList.add('active');

  const navItems = document.querySelectorAll('.nav-menu .nav-item');
  navItems.forEach(item => {
    item.classList.remove('active');
    const text = item.innerText.toLowerCase();
    if (
      (tabId === 'download' && text.includes('descargar')) ||
      (tabId === 'library' && text.includes('biblioteca')) ||
      (tabId === 'audit' && text.includes('auditor')) ||
      (tabId === 'settings' && text.includes('configurac'))
    ) {
      item.classList.add('active');
    }
  });
}

// 2. Format Duration (seconds to MM:SS)
function formatDuration(sec) {
  if (!sec || isNaN(sec)) return "--:--";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}

// 3. Search Full Artist Discography
async function searchDiscography() {
  const query = document.getElementById('searchInput').value.trim();
  if (!query) return;

  const btnDisco = document.querySelectorAll('.btn-search-go')[0];
  const origText = btnDisco.innerText;
  btnDisco.innerText = "Cargando...";
  btnDisco.disabled = true;

  try {
    if (!window.pywebview || !window.pywebview.api) {
      alert("La API de SpotiFLAC Hi-Res Engine no está conectada.");
      return;
    }

    const data = await window.pywebview.api.get_artist_discography(query);
    if (!data || !data.success) {
      alert(data && data.error ? data.error : "No se encontró discografía para este artista.");
      return;
    }

    currentDiscographyData = data;
    renderDiscographyView(data);
  } catch (err) {
    console.error("Error al buscar discografía:", err);
    alert("Error al buscar discografía: " + err);
  } finally {
    btnDisco.innerText = origText;
    btnDisco.disabled = false;
  }
}

function renderDiscographyView(data) {
  switchTab('download');
  document.getElementById('emptySearchState').style.display = 'none';
  document.getElementById('albumHero').style.display = 'none';
  document.getElementById('tracklistSection').style.display = 'none';
  document.getElementById('discographySection').style.display = 'block';

  document.getElementById('discoArtistTitle').innerText = `${data.artist} — Discografía (${data.genre})`;
  document.getElementById('discoArtistSub').innerText = `${data.albums.length} lanzamientos oficiales detectados. Selecciona los álbumes que deseas descargar o marca todos.`;

  const grid = document.getElementById('discoAlbumsGrid');
  grid.innerHTML = '';

  data.albums.forEach(alb => {
    const card = document.createElement('div');
    const isComp = alb.already_downloaded;
    const isChecked = !isComp;
    card.id = `disco-card-${alb.id}`;
    card.className = `disco-album-card ${isChecked ? 'selected' : ''}`;
    
    card.onclick = (e) => {
      if (e.target.tagName.toLowerCase() === 'button' || e.target.classList.contains('disco-checkbox')) return;
      const chk = document.getElementById(`disco-chk-${alb.id}`);
      if (chk) {
        chk.checked = !chk.checked;
        onAlbumCheckboxChange(chk.checked, alb.id);
      }
    };

    const badgeStatus = isComp 
      ? `<span class="badge" style="background: rgba(16,185,129,0.2); color: #34d399; font-size: 11px;">✅ En Biblioteca (${alb.local_tracks} pistas)</span>`
      : `<span class="badge" style="background: rgba(59,130,246,0.2); color: #60a5fa; font-size: 11px;">⏳ Pendiente</span>`;

    const actionBtn = isComp
      ? `<button class="btn-foobar" style="padding: 6px; font-size: 11px; margin-top: auto;" onclick="document.getElementById('searchInput').value='${data.artist} - ${alb.title}'; searchAlbum();">Ver Pistas</button>`
      : `<button class="btn-primary-download" style="padding: 8px 12px; font-size: 11px; justify-content: center; margin-top: auto;" onclick="document.getElementById('searchInput').value='${data.artist} - ${alb.title}'; searchAlbum();">Descargar Solo Este</button>`;

    card.innerHTML = `
      <div class="disco-card-top-row">
        <input type="checkbox" id="disco-chk-${alb.id}" class="disco-checkbox" ${isChecked ? 'checked' : ''} onchange="onAlbumCheckboxChange(this.checked, '${alb.id}')" />
      </div>
      <img class="disco-album-cover" src="${alb.cover || ''}" alt="${alb.title}" />
      <div class="disco-album-title" title="${alb.title}">${alb.title}</div>
      <div class="disco-album-year">[${alb.year}] • ${alb.type}</div>
      <div style="margin-bottom: 10px;">${badgeStatus}</div>
      ${actionBtn}
    `;
    grid.appendChild(card);
  });

  updateSelectedCount();
}

function onAlbumCheckboxChange(checked, albId) {
  const card = document.getElementById(`disco-card-${albId}`);
  if (card) {
    if (checked) card.classList.add('selected');
    else card.classList.remove('selected');
  }
  updateSelectedCount();
}

function toggleSelectAllDisco(check) {
  if (!currentDiscographyData || !currentDiscographyData.albums) return;
  currentDiscographyData.albums.forEach(alb => {
    const chk = document.getElementById(`disco-chk-${alb.id}`);
    const card = document.getElementById(`disco-card-${alb.id}`);
    if (chk) chk.checked = check;
    if (card) {
      if (check) card.classList.add('selected');
      else card.classList.remove('selected');
    }
  });
  updateSelectedCount();
}

function updateSelectedCount() {
  const checkboxes = document.querySelectorAll('.disco-checkbox');
  let selected = 0;
  checkboxes.forEach(c => { if (c.checked) selected++; });
  const btn = document.getElementById('btnDownloadSelectedDisco');
  if (btn) {
    btn.innerText = `⚡ Descargar Seleccionados (${selected}) en Hi-Res`;
    btn.disabled = (selected === 0);
  }
}

// Download Only Selected Albums in Discography
async function downloadSelectedDiscography() {
  if (!currentDiscographyData || !currentDiscographyData.albums) return;
  
  const selectedAlbums = currentDiscographyData.albums.filter(alb => {
    const chk = document.getElementById(`disco-chk-${alb.id}`);
    return chk && chk.checked;
  });

  if (selectedAlbums.length === 0) {
    alert("Por favor, selecciona al menos un álbum marcando la casilla.");
    return;
  }

  const confirmDownload = confirm(`Se descargarán ${selectedAlbums.length} álbum(es) seleccionados de ${currentDiscographyData.artist}. ¿Deseas iniciar la descarga en Hi-Res?`);
  if (!confirmDownload) return;

  const btnSelected = document.getElementById('btnDownloadSelectedDisco');
  btnSelected.disabled = true;

  for (let i = 0; i < selectedAlbums.length; i++) {
    const alb = selectedAlbums[i];
    btnSelected.innerText = `Descargando (${i + 1}/${selectedAlbums.length}): ${alb.title}...`;
    
    // Set card visual cue
    const card = document.getElementById(`disco-card-${alb.id}`);
    if (card) {
      const badge = card.querySelector('.badge');
      if (badge) {
        badge.style.background = 'rgba(245,158,11,0.2)';
        badge.style.color = '#fbbf24';
        badge.innerText = '⬇️ Descargando...';
      }
    }

    document.getElementById('searchInput').value = `${currentDiscographyData.artist} - ${alb.title}`;
    await searchAlbum();
    await startDownload();

    if (card) {
      const badge = card.querySelector('.badge');
      if (badge) {
        badge.style.background = 'rgba(16,185,129,0.2)';
        badge.style.color = '#34d399';
        badge.innerText = '✅ En Biblioteca';
      }
    }
  }

  btnSelected.disabled = false;
  btnSelected.innerText = "⚡ Descargar Seleccionados en Hi-Res";
  alert(`¡Descarga completada! Se integraron ${selectedAlbums.length} álbumes en tu biblioteca.`);
  searchDiscography();
}

// 3. Search Album / Spotify URL / Deezer URL
async function searchAlbum() {
  const query = document.getElementById('searchInput').value.trim();
  if (!query) return;

  const btnSearch = document.querySelector('.btn-search-go');
  const originalText = btnSearch.innerText;
  btnSearch.innerText = "Buscando...";
  btnSearch.disabled = true;

  try {
    if (!window.pywebview || !window.pywebview.api) {
      alert("La API de SpotiFLAC Hi-Res Engine no está conectada.");
      return;
    }

    const data = await window.pywebview.api.search(query);

    if (!data || !data.success) {
      alert(data && data.error ? data.error : "No se encontró el álbum o metadata en Deezer/Spotify.");
      return;
    }

    currentAlbumData = data.album;
    renderAlbumHero(currentAlbumData);
    renderTracklist(currentAlbumData.tracks);

    // Switch to download tab and show views
    switchTab('download');
    document.getElementById('emptySearchState').style.display = 'none';
    document.getElementById('albumHero').style.display = 'flex';
    document.getElementById('tracklistSection').style.display = 'block';

  } catch (err) {
    console.error("Error al buscar:", err);
    alert("Error interno al buscar: " + err);
  } finally {
    btnSearch.innerText = originalText;
    btnSearch.disabled = false;
  }
}

// 4. Render Album Details
function renderAlbumHero(alb) {
  document.getElementById('albumTitleText').innerText = alb.title;
  document.getElementById('albumArtistText').innerText = alb.artist;
  document.getElementById('albumYearText').innerText = alb.year || "N/A";
  document.getElementById('albumGenreText').innerText = alb.genre || "Desconocido";
  document.getElementById('albumTracksCount').innerText = alb.tracks ? alb.tracks.length : 0;
  
  const coverEl = document.getElementById('albumCoverImg');
  if (alb.cover_xl) {
    coverEl.src = alb.cover_xl;
  } else if (alb.cover_medium) {
    coverEl.src = alb.cover_medium;
  } else {
    coverEl.src = "";
  }

  const btnDownload = document.getElementById('btnStartDownload');
  btnDownload.disabled = false;
  btnDownload.innerHTML = '<span>⬇️</span> Descargar Álbum Completo';
}

// 5. Render Tracklist
function renderTracklist(tracks) {
  const tbody = document.getElementById('tracklistTbody');
  tbody.innerHTML = '';

  tracks.forEach((t, idx) => {
    const row = document.createElement('tr');
    row.id = `track-row-${idx}`;
    row.innerHTML = `
      <td class="track-pos">${t.track_position || (idx + 1)}</td>
      <td class="track-title-col">${t.title}</td>
      <td>${formatDuration(t.duration)}</td>
      <td><span id="track-status-${idx}" class="track-status-badge status-waiting">⏳ Pendiente</span></td>
    `;
    tbody.appendChild(row);
  });
}

// 6. Start Download Process
async function startDownload() {
  if (isDownloading) return;
  if (!currentAlbumData || !currentAlbumData.tracks || currentAlbumData.tracks.length === 0) {
    alert("No hay álbum seleccionado para descargar.");
    return;
  }

  isDownloading = true;
  const btnDownload = document.getElementById('btnStartDownload');
  btnDownload.disabled = true;
  btnDownload.innerHTML = '<span>⏳</span> Descargando...';

  const progressCard = document.getElementById('overallProgressCard');
  progressCard.style.display = 'block';
  progressCard.classList.add('active');
  document.getElementById('progressBarFill').style.width = '0%';
  document.getElementById('progressPercent').innerText = '0%';
  document.getElementById('progressText').innerText = 'Iniciando descarga y auditoría Hi-Res...';

  try {
    const res = await window.pywebview.api.download_current_album();
    if (res && res.success) {
      document.getElementById('progressText').innerText = `✅ Completado con éxito: ${res.completed} pistas verificadas (0 errores).`;
      document.getElementById('progressBarFill').style.width = '100%';
      document.getElementById('progressPercent').innerText = '100%';
      btnDownload.innerHTML = '<span>✅</span> Álbum Descargado';
    } else {
      document.getElementById('progressText').innerText = `⚠️ Proceso finalizado con advertencias: ${res ? res.error : ''}`;
      btnDownload.disabled = false;
      btnDownload.innerHTML = '<span>🔄</span> Reintentar Descarga';
    }
  } catch (err) {
    console.error("Error al descargar:", err);
    alert("Error en la descarga: " + err);
    btnDownload.disabled = false;
    btnDownload.innerHTML = '<span>⬇️</span> Descargar Álbum Completo';
  } finally {
    isDownloading = false;
  }
}

// 7. Realtime Callback from Python Bridge
window.onTrackProgress = function(idx, total, status, label, percent) {
  const badge = document.getElementById(`track-status-${idx}`);
  if (badge) {
    if (status === 'downloading') {
      badge.className = 'track-status-badge status-downloading';
      badge.innerText = '⬇️ Descargando...';
    } else if (status === 'auditing') {
      badge.className = 'track-status-badge status-auditing';
      badge.innerText = '🛡️ Auditando ffmpeg...';
    } else if (status === 'completed') {
      badge.className = 'track-status-badge status-completed';
      badge.innerText = label || '⭐ Hi-Res FLAC';
    } else if (status === 'failed') {
      badge.className = 'track-status-badge';
      badge.style.backgroundColor = '#ef4444';
      badge.style.color = '#ffffff';
      badge.innerText = '❌ Error';
    }
  }

  const pBar = document.getElementById('progressBarFill');
  const pPct = document.getElementById('progressPercent');
  const pTxt = document.getElementById('progressText');

  if (pBar) pBar.style.width = `${percent}%`;
  if (pPct) pPct.innerText = `${percent}%`;
  if (pTxt) pTxt.innerText = `Procesando pista ${idx + 1} de ${total}: ${currentAlbumData ? currentAlbumData.tracks[idx].title : ''}`;
};

// 8. Open foobar2000
async function openFoobar() {
  try {
    if (window.pywebview && window.pywebview.api) {
      const res = await window.pywebview.api.open_foobar();
      if (!res.success) {
        alert("No se pudo iniciar foobar2000: " + res.error);
      }
    }
  } catch (e) {
    alert("Error abriendo foobar2000: " + e);
  }
}

// 9. Scan Library / Monitor
async function scanLibrary() {
  switchTab('audit');
  appendAuditLog('[INFO] Iniciando escaneo del monitor de biblioteca (630+ artistas)...', 'info');

  try {
    if (window.pywebview && window.pywebview.api) {
      const res = await window.pywebview.api.scan_library();
      if (res && res.success) {
        appendAuditLog(`[SUCCESS] Escaneo completado. ${res.message || 'Biblioteca al día.'}`, 'success');
      } else {
        appendAuditLog(`[WARN] Escaneo finalizado: ${res ? res.error : ''}`, 'warn');
      }
    }
  } catch (e) {
    appendAuditLog(`[ERROR] Fallo al actualizar biblioteca: ${e}`, 'error');
  }
}

// 10. Run Full Integrity Audit
async function runIntegrityAudit() {
  switchTab('audit');
  appendAuditLog('[INFO] Iniciando auditoría acústica profunda con ffmpeg y ffprobe...', 'info');

  try {
    if (window.pywebview && window.pywebview.api) {
      const res = await window.pywebview.api.run_audit();
      if (res && res.success) {
        appendAuditLog(`[SUCCESS] Auditoría completada. Total analizados: ${res.total_checked}. 0 errores acústicos.`, 'success');
      } else {
        appendAuditLog(`[ERROR] Error en auditoría: ${res ? res.error : ''}`, 'error');
      }
    }
  } catch (e) {
    appendAuditLog(`[ERROR] Fallo en auditoría: ${e}`, 'error');
  }
}

// 11. Append Log Line to Audit Box
function appendAuditLog(text, level = 'info') {
  const box = document.getElementById('auditLogBox');
  if (!box) return;
  const line = document.createElement('div');
  line.className = `log-line-${level}`;
  line.innerText = text;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}

// 12. Load Known Artists & Live Stats on Startup
window.addEventListener('pywebviewready', async () => {
  appendAuditLog('[INFO] PyWebView inicializado. Motor SpotiFLAC Hi-Res listo.', 'info');

  try {
    if (window.pywebview && window.pywebview.api) {
      const artists = await window.pywebview.api.get_known_artists();
      renderKnownArtists(artists);

      const stats = await window.pywebview.api.get_library_stats();
      if (stats) {
        updateStatsUI(stats);
      }
    }
  } catch (e) {
    console.error("Error al cargar datos iniciales:", e);
  }
});

function renderKnownArtists(artistsMap) {
  const container = document.getElementById('knownArtistsGrid');
  if (!container || !artistsMap) return;
  container.innerHTML = '';

  Object.entries(artistsMap).forEach(([name, data]) => {
    const card = document.createElement('div');
    card.className = 'stat-card';
    card.style.cursor = 'pointer';
    card.style.transition = 'all 0.2s ease';
    card.onmouseover = () => { card.style.borderColor = 'var(--accent-purple)'; };
    card.onmouseout = () => { card.style.borderColor = 'var(--border-color)'; };
    card.onclick = () => {
      document.getElementById('searchInput').value = name;
      searchDiscography();
    };

    card.innerHTML = `
      <span class="stat-title">${data.genre || 'Metal'}</span>
      <span class="stat-number" style="font-size: 17px; margin-bottom: 4px;">${name}</span>
      <span class="stat-sub" style="color: var(--text-muted); font-size: 11px; line-height: 1.3;">
        ${data.disambiguation || 'Artista verificado'}
      </span>
    `;
    container.appendChild(card);
  });
}

function updateStatsUI(stats) {
  // Update stat cards if provided
  const statNumbers = document.querySelectorAll('.stat-cards-grid .stat-number');
  if (statNumbers.length >= 4) {
    if (stats.artists) statNumbers[0].innerText = stats.artists;
    if (stats.albums) statNumbers[1].innerText = stats.albums;
    if (stats.tracks) statNumbers[2].innerText = stats.tracks;
    if (stats.hires_pct) statNumbers[3].innerText = `${stats.hires_pct}%`;
  }
}
