from pathlib import Path
import shutil
import tempfile

import streamlit.components.v1 as components


_PATCH_MARKER = "/* FS_SWIPE_DOWN_PASS_PATCH_V14 */"


def _replace_all(content, replacements):
    updated = content
    for old, new in replacements:
        updated = updated.replace(old, new)
    return updated


def _js_replacements():
    return [
        (
            '<button class="action-btn btn-pass" onclick="swipeCards.swipeLeft()" disabled>❌</button>',
            '<button class="action-btn btn-disagree" onclick="swipeCards.swipeLeft()" disabled><span class="fs-swipe-icon fs-left" aria-hidden="true"></span><span class="fs-swipe-copy"><b>👎 DISAGREE</b><small>SWIPE LEFT</small></span></button>',
        ),
        (
            '<button class="action-btn btn-disagree" onclick="swipeCards.swipeLeft()" disabled>DISAGREE</button>',
            '<button class="action-btn btn-disagree" onclick="swipeCards.swipeLeft()" disabled><span class="fs-swipe-icon fs-left" aria-hidden="true"></span><span class="fs-swipe-copy"><b>👎 DISAGREE</b><small>SWIPE LEFT</small></span></button>',
        ),
        (
            '<button class="action-btn btn-pass" onclick="swipeCards.swipeLeft()">❌</button>',
            '<button class="action-btn btn-disagree" onclick="swipeCards.swipeLeft()"><span class="fs-swipe-icon fs-left" aria-hidden="true"></span><span class="fs-swipe-copy"><b>👎 DISAGREE</b><small>SWIPE LEFT</small></span></button>',
        ),
        (
            '<button class="action-btn btn-disagree" onclick="swipeCards.swipeLeft()">DISAGREE</button>',
            '<button class="action-btn btn-disagree" onclick="swipeCards.swipeLeft()"><span class="fs-swipe-icon fs-left" aria-hidden="true"></span><span class="fs-swipe-copy"><b>👎 DISAGREE</b><small>SWIPE LEFT</small></span></button>',
        ),
        (
            '<button class="action-btn btn-like" onclick="swipeCards.swipeRight()" disabled>✔️</button>',
            '<button class="action-btn btn-like" onclick="swipeCards.swipeRight()" disabled><span class="fs-swipe-icon fs-right" aria-hidden="true"></span><span class="fs-swipe-copy"><b>👍 AGREE</b><small>SWIPE RIGHT</small></span></button>',
        ),
        (
            '<button class="action-btn btn-like" onclick="swipeCards.swipeRight()" disabled>AGREE</button>',
            '<button class="action-btn btn-like" onclick="swipeCards.swipeRight()" disabled><span class="fs-swipe-icon fs-right" aria-hidden="true"></span><span class="fs-swipe-copy"><b>👍 AGREE</b><small>SWIPE RIGHT</small></span></button>',
        ),
        (
            '<button class="action-btn btn-like" onclick="swipeCards.swipeRight()">✔️</button>',
            '<button class="action-btn btn-like" onclick="swipeCards.swipeRight()"><span class="fs-swipe-icon fs-right" aria-hidden="true"></span><span class="fs-swipe-copy"><b>👍 AGREE</b><small>SWIPE RIGHT</small></span></button>',
        ),
        (
            '<button class="action-btn btn-like" onclick="swipeCards.swipeRight()">AGREE</button>',
            '<button class="action-btn btn-like" onclick="swipeCards.swipeRight()"><span class="fs-swipe-icon fs-right" aria-hidden="true"></span><span class="fs-swipe-copy"><b>👍 AGREE</b><small>SWIPE RIGHT</small></span></button>',
        ),
        (
            '<button class="action-btn btn-back" onclick="swipeCards.goBack()">',
            '<button class="action-btn btn-pass" onclick="swipeCards.swipeDown()"><span class="fs-swipe-icon fs-down" aria-hidden="true"></span><span class="fs-swipe-copy"><b>⏭ PASS</b><small>SWIPE DOWN</small></span></button>\n'
            '          <button class="action-btn btn-back" onclick="swipeCards.goBack()">',
        ),
        (
            '<button class="action-btn btn-pass" onclick="swipeCards.swipeDown()">PASS</button>',
            '<button class="action-btn btn-pass" onclick="swipeCards.swipeDown()"><span class="fs-swipe-icon fs-down" aria-hidden="true"></span><span class="fs-swipe-copy"><b>⏭ PASS</b><small>SWIPE DOWN</small></span></button>',
        ),
        (
            '<div class="action-indicator like">✔️</div>\n          <div class="action-indicator pass">❌</div>',
            '<div class="action-indicator like"><span class="fs-swipe-icon fs-right"></span><span class="fs-ind-copy"><b>👍 AGREE</b><small>SWIPE RIGHT</small></span></div>\n'
            '          <div class="action-indicator pass"><span class="fs-swipe-icon fs-left"></span><span class="fs-ind-copy"><b>👎 DISAGREE</b><small>SWIPE LEFT</small></span></div>\n'
            '          <div class="action-indicator down"><span class="fs-swipe-icon fs-down"></span><span class="fs-ind-copy"><b>⏭ PASS</b><small>SWIPE DOWN</small></span></div>',
        ),
        (
            '<div class="action-indicator like">AGREE</div>\n'
            '          <div class="action-indicator pass">DISAGREE</div>\n'
            '          <div class="action-indicator down">PASS</div>',
            '<div class="action-indicator like"><span class="fs-swipe-icon fs-right"></span><span class="fs-ind-copy"><b>👍 AGREE</b><small>SWIPE RIGHT</small></span></div>\n'
            '          <div class="action-indicator pass"><span class="fs-swipe-icon fs-left"></span><span class="fs-ind-copy"><b>👎 DISAGREE</b><small>SWIPE LEFT</small></span></div>\n'
            '          <div class="action-indicator down"><span class="fs-swipe-icon fs-down"></span><span class="fs-ind-copy"><b>⏭ PASS</b><small>SWIPE DOWN</small></span></div>',
        ),
        (
            "          const likeIndicator = topCard.querySelector('.action-indicator.like');\n"
            "          const passIndicator = topCard.querySelector('.action-indicator.pass');\n\n"
            "          if (deltaX > 50) {\n"
            "            likeIndicator.classList.add('show');\n"
            "            passIndicator.classList.remove('show');\n"
            "          } else if (deltaX < -50) {\n"
            "            passIndicator.classList.add('show');\n"
            "            likeIndicator.classList.remove('show');\n"
            "          } else {\n"
            "            likeIndicator.classList.remove('show');\n"
            "            passIndicator.classList.remove('show');\n"
            "          }",
            "          const likeIndicator = topCard.querySelector('.action-indicator.like');\n"
            "          const passIndicator = topCard.querySelector('.action-indicator.pass');\n"
            "          const downIndicator = topCard.querySelector('.action-indicator.down');\n\n"
            "          const isDownGesture = deltaY > 50 && Math.abs(deltaY) > Math.abs(deltaX) + 20;\n"
            "          if (isDownGesture) {\n"
            "            downIndicator.classList.add('show');\n"
            "            likeIndicator.classList.remove('show');\n"
            "            passIndicator.classList.remove('show');\n"
            "          } else if (deltaX > 50) {\n"
            "            likeIndicator.classList.add('show');\n"
            "            passIndicator.classList.remove('show');\n"
            "            downIndicator.classList.remove('show');\n"
            "          } else if (deltaX < -50) {\n"
            "            passIndicator.classList.add('show');\n"
            "            likeIndicator.classList.remove('show');\n"
            "            downIndicator.classList.remove('show');\n"
            "          } else {\n"
            "            likeIndicator.classList.remove('show');\n"
            "            passIndicator.classList.remove('show');\n"
            "            downIndicator.classList.remove('show');\n"
            "          }",
        ),
        (
            "    const deltaX = this.currentX - this.startX;\n"
            "    const topCard = this.container.querySelector('.swipe-card:first-child');\n"
            "    \n"
            "    if (topCard) {\n"
            "      topCard.classList.remove('dragging');\n"
            "      \n"
            "      // Determine swipe direction\n"
            "      if (Math.abs(deltaX) > 100) {\n"
            "        if (deltaX > 0) {\n"
            "          this.swipeRight();\n"
            "        } else {\n"
            "          this.swipeLeft();\n"
            "        }\n"
            "      } else {\n"
            "        // Snap back to center\n"
            "        topCard.style.transform = '';\n"
            "        topCard.querySelector('.action-indicator.like').classList.remove('show');\n"
            "        topCard.querySelector('.action-indicator.pass').classList.remove('show');\n"
            "      }\n"
            "    }",
            "    const deltaX = this.currentX - this.startX;\n"
            "    const deltaY = this.currentY - this.startY;\n"
            "    const topCard = this.container.querySelector('.swipe-card:first-child');\n"
            "    \n"
            "    if (topCard) {\n"
            "      topCard.classList.remove('dragging');\n"
            "      \n"
            "      // Determine swipe direction\n"
            "      if (deltaY > 100 && Math.abs(deltaY) > Math.abs(deltaX) + 20) {\n"
            "        this.swipeDown();\n"
            "      } else if (Math.abs(deltaX) > 100) {\n"
            "        if (deltaX > 0) {\n"
            "          this.swipeRight();\n"
            "        } else {\n"
            "          this.swipeLeft();\n"
            "        }\n"
            "      } else {\n"
            "        // Snap back to center\n"
            "        topCard.style.transform = '';\n"
            "        topCard.querySelector('.action-indicator.like').classList.remove('show');\n"
            "        topCard.querySelector('.action-indicator.pass').classList.remove('show');\n"
            "        topCard.querySelector('.action-indicator.down').classList.remove('show');\n"
            "      }\n"
            "    }",
        ),
        (
            "  goBack() {",
            "  swipeDown() {\n"
            "    if (this.mode !== 'swipe') {\n"
            "      this.showNotification('Press \"Swipe\" to be able to swipe');\n"
            "      return;\n"
            "    }\n"
            "    if (this.isAnimating) return;\n"
            "    this.isAnimating = true;\n"
            "    const topCard = this.container.querySelector('.swipe-card:first-child');\n"
            "    const card = this.cards[this.currentIndex];\n"
            "\n"
            "    if (topCard && card) {\n"
            "      topCard.classList.add('swiped-down');\n"
            "\n"
            "      this.swipedCards.push({ index: this.currentIndex, action: 'down' });\n"
            "      this.lastAction = { action: 'down', cardIndex: this.currentIndex };\n"
            "\n"
            "      setTimeout(() => {\n"
            "        this.currentIndex++;\n"
            "        topCard.remove();\n"
            "        this.addNewCardToStack();\n"
            "        this.updateCardStackClasses();\n"
            "        this.updateSwipeCounter();\n"
            "        this.bindEvents();\n"
            "        if (this.currentIndex >= this.cards.length) {\n"
            "          this.render();\n"
            "        }\n"
            "        this.sendResults();\n"
            "        this.isAnimating = false;\n"
            "        updateFrameHeightDebounced();\n"
            "      }, 300);\n"
            "    }\n"
            "  }\n\n"
            "  goBack() {",
        ),
        (
            "      const directionClass =\n"
            "        lastSwiped.action === 'left' ? 'return-from-left' : 'return-from-right';\n"
            "      topCard.classList.add(directionClass);\n"
            "      setTimeout(() => {\n"
            "        topCard.classList.remove('return-from-left', 'return-from-right');\n"
            "        this.isAnimating = false;\n"
            "        updateFrameHeightDebounced();\n"
            "      }, 300);",
            "      const directionClass =\n"
            "        lastSwiped.action === 'left'\n"
            "          ? 'return-from-left'\n"
            "          : lastSwiped.action === 'down'\n"
            "            ? 'return-from-down'\n"
            "            : 'return-from-right';\n"
            "      topCard.classList.add(directionClass);\n"
            "      setTimeout(() => {\n"
            "        topCard.classList.remove('return-from-left', 'return-from-right', 'return-from-down');\n"
            "        this.isAnimating = false;\n"
            "        updateFrameHeightDebounced();\n"
            "      }, 300);",
        ),
    ]


def _css_append():
    return f"""

{_PATCH_MARKER}
.swipe-card.swiped-down {{
  transform: translateY(420px) rotate(6deg);
  opacity: 0;
}}

.return-from-down {{
  animation: return-from-down 0.3s ease-out;
}}

@keyframes return-from-down {{
  from {{
    transform: translateY(420px) rotate(6deg);
    opacity: 0;
  }}
  to {{
    transform: translateX(0) translateY(0) rotate(0);
    opacity: 1;
  }}
}}

.action-buttons {{
  width: 100% !important;
  max-width: 420px;
  display: flex !important;
  flex-wrap: wrap !important;
  justify-content: center !important;
  align-items: center !important;
  gap: 8px;
}}

.action-btn {{
  width: auto !important;
  min-width: 78px;
  min-height: 58px !important;
  height: auto !important;
  border-radius: 999px !important;
  padding: 6px 12px;
  font-size: 12px !important;
  line-height: 1.15 !important;
  text-align: left !important;
  white-space: normal !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
  letter-spacing: 0.03em;
}}

.fs-swipe-icon {{
  width: 34px;
  height: 24px;
  flex: 0 0 34px;
  background-repeat: no-repeat;
  background-size: contain;
  background-position: center;
}}

.fs-left {{
  background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAxMjAgNzInPjxnIGZpbGw9J25vbmUnIHN0cm9rZT0nIzBCM0E1Micgc3Ryb2tlLXdpZHRoPSc1JyBzdHJva2UtbGluZWNhcD0ncm91bmQnIHN0cm9rZS1saW5lam9pbj0ncm91bmQnPjxwYXRoIGQ9J002NCA1OFYyNGMwLTQgMy03IDctN3M3IDMgNyA3djE4Jy8+PHBhdGggZD0nTTcxIDU4SDQ3Yy03IDAtMTItNS0xMi0xMlYzM2MwLTQgMy03IDctN3M3IDMgNyA3djcnLz48Y2lyY2xlIGN4PSc2NCcgY3k9JzE4JyByPSc4Jy8+PHBhdGggZD0nTTI0IDE4bC0xMCA4IDEwIDgnLz48cGF0aCBkPSdNMzggMThsLTEwIDggMTAgOCcvPjwvZz48L3N2Zz4=");
}}

.fs-right {{
  background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAxMjAgNzInPjxnIGZpbGw9J25vbmUnIHN0cm9rZT0nIzBCM0E1Micgc3Ryb2tlLXdpZHRoPSc1JyBzdHJva2UtbGluZWNhcD0ncm91bmQnIHN0cm9rZS1saW5lam9pbj0ncm91bmQnPjxwYXRoIGQ9J001NiA1OFYyNGMwLTQtMy03LTctN3MtNyAzLTcgN3YxOCcvPjxwYXRoIGQ9J000OSA1OGgyNGM3IDAgMTItNSAxMi0xMlYzM2MwLTQtMy03LTctN3MtNyAzLTcgN3Y3Jy8+PGNpcmNsZSBjeD0nNTYnIGN5PScxOCcgcj0nOCcvPjxwYXRoIGQ9J004MiAxOGwxMCA4LTEwIDgnLz48cGF0aCBkPSdNNjggMThsMTAgOC0xMCA4Jy8+PC9nPjwvc3ZnPg==");
}}

.fs-down {{
  background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAxMjAgNzInPjxnIGZpbGw9J25vbmUnIHN0cm9rZT0nIzBCM0E1Micgc3Ryb2tlLXdpZHRoPSc1JyBzdHJva2UtbGluZWNhcD0ncm91bmQnIHN0cm9rZS1saW5lam9pbj0ncm91bmQnPjxwYXRoIGQ9J002MyAxNnYyN2MwIDctNSAxMi0xMiAxMkgzN2MtNCAwLTctMy03LTdzMy03IDctN2g3Jy8+PHBhdGggZD0nTTYzIDIzYzAtNCAzLTcgNy03czcgMyA3IDd2MjAnLz48Y2lyY2xlIGN4PSc2MycgY3k9JzEyJyByPSc4Jy8+PHBhdGggZD0nTTE2IDM0bDggMTAgOC0xMCcvPjxwYXRoIGQ9J00xNiA0OGw4IDEwIDgtMTAnLz48L2c+PC9zdmc+");
}}

.fs-swipe-copy {{
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.05;
}}

.fs-swipe-copy b {{
  font-size: 11px;
}}

.fs-swipe-copy small {{
  font-size: 10px;
  letter-spacing: 0.04em;
}}

.btn-disagree,
.btn-pass,
.btn-like {{
  order: 1;
  flex: 1 1 30%;
}}

.btn-back {{
  order: 2;
  flex: 0 0 70px;
  margin-top: 2px;
}}

.btn-disagree {{
  background: var(--btn-pass-bg, #FFFFFF);
  color: var(--btn-pass-fg, #0B3A52);
}}

.action-indicator {{
  font-size: 14px !important;
  line-height: 1.25 !important;
  text-align: center !important;
  padding: 7px 10px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.25);
  color: #fff !important;
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
}}

.action-indicator .fs-swipe-icon {{
  filter: brightness(0) invert(1);
  width: 26px;
  height: 18px;
  flex: 0 0 26px;
}}

.fs-ind-copy {{
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.05;
}}

.fs-ind-copy b {{
  font-size: 11px;
}}

.fs-ind-copy small {{
  font-size: 9px;
  letter-spacing: 0.04em;
}}

.action-indicator.like {{
  right: 16px;
  color: #fff !important;
}}

.action-indicator.pass {{
  left: 16px;
  color: #fff !important;
}}

.action-indicator.down {{
  left: 50%;
  transform: translate(-50%, 0);
  bottom: 16px;
  top: auto;
  color: #fff !important;
}}

/* Avoid top/bottom clipping of tall card images on mobile */
.cards-stack {{
  width: min(92vw, 520px) !important;
  height: min(92vw, 520px) !important;
  max-width: 520px !important;
  max-height: 520px !important;
  margin: 0 auto 8px auto !important;
}}

.swipe-card {{
  width: 100% !important;
  height: 100% !important;
}}

.swipe-card .card-image {{
  height: 100% !important;
  object-fit: contain !important;
  background: transparent !important;
  border-radius: 16px !important;
}}

.swipe-card .card-content {{
  display: none !important;
}}

@media (max-width: 480px) {{
  .cards-stack {{
    width: min(94vw, 440px) !important;
    height: min(94vw, 440px) !important;
    max-width: 440px !important;
    max-height: 440px !important;
  }}
}}
"""


def _build_patched_frontend_dir(package_root: Path):
    source_frontend = package_root / "frontend"
    if not source_frontend.exists():
        return None

    base_temp = Path(tempfile.gettempdir()) / "fs_swipecards_patch_v14"
    target_frontend = base_temp / "frontend"

    if not target_frontend.exists():
        if base_temp.exists():
            shutil.rmtree(base_temp, ignore_errors=True)
        target_frontend.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_frontend, target_frontend, dirs_exist_ok=True)

    js_path = target_frontend / "main.js"
    css_path = target_frontend / "style.css"
    if not js_path.exists() or not css_path.exists():
        return None

    js = js_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")

    if _PATCH_MARKER not in js:
        js = _replace_all(js, _js_replacements())
        js += f"\n\n{_PATCH_MARKER}\n"
        js_path.write_text(js, encoding="utf-8")
    if _PATCH_MARKER not in css:
        css += _css_append()
        css_path.write_text(css, encoding="utf-8")

    return target_frontend


def load_streamlit_swipecards():
    try:
        import streamlit_swipecards as _sc
    except Exception:
        return None

    try:
        package_root = Path(_sc.__file__).resolve().parent
        patched_frontend = _build_patched_frontend_dir(package_root)
        if patched_frontend:
            _sc._component_func = components.declare_component(
                "streamlit_swipecards_fs_patch",
                path=str(patched_frontend),
            )
    except Exception:
        # Keep graceful fallback to original dependency.
        pass

    return _sc.streamlit_swipecards
