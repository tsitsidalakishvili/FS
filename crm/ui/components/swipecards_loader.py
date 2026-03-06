from pathlib import Path


_PATCH_MARKER = "/* FS_SWIPE_DOWN_PASS_PATCH_V1 */"


def _replace_all(content, replacements):
    updated = content
    for old, new in replacements:
        if old in updated:
            updated = updated.replace(old, new)
    return updated


def _patch_frontend_files(package_root: Path):
    frontend_dir = package_root / "frontend"
    js_path = frontend_dir / "main.js"
    css_path = frontend_dir / "style.css"
    if not js_path.exists() or not css_path.exists():
        return

    js = js_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    if _PATCH_MARKER in js and _PATCH_MARKER in css:
        return

    js_replacements = [
        (
            '<button class="action-btn btn-pass" onclick="swipeCards.swipeLeft()" disabled>❌</button>',
            '<button class="action-btn btn-disagree" onclick="swipeCards.swipeLeft()" disabled>DISAGREE</button>',
        ),
        (
            '<button class="action-btn btn-pass" onclick="swipeCards.swipeLeft()">❌</button>',
            '<button class="action-btn btn-disagree" onclick="swipeCards.swipeLeft()">DISAGREE</button>',
        ),
        (
            '<button class="action-btn btn-like" onclick="swipeCards.swipeRight()" disabled>✔️</button>',
            '<button class="action-btn btn-like" onclick="swipeCards.swipeRight()" disabled>AGREE</button>',
        ),
        (
            '<button class="action-btn btn-like" onclick="swipeCards.swipeRight()">✔️</button>',
            '<button class="action-btn btn-like" onclick="swipeCards.swipeRight()">AGREE</button>',
        ),
        (
            '<button class="action-btn btn-back" onclick="swipeCards.goBack()">',
            '<button class="action-btn btn-pass" onclick="swipeCards.swipeDown()">PASS</button>\n'
            '          <button class="action-btn btn-back" onclick="swipeCards.goBack()">',
        ),
        (
            '<div class="action-indicator like">✔️</div>\n          <div class="action-indicator pass">❌</div>',
            '<div class="action-indicator like">AGREE</div>\n'
            '          <div class="action-indicator pass">DISAGREE</div>\n'
            '          <div class="action-indicator down">PASS</div>',
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
    js = _replace_all(js, js_replacements)
    if _PATCH_MARKER not in js:
        js += f"\n\n{_PATCH_MARKER}\n"
    js_path.write_text(js, encoding="utf-8")

    css_append = f"""

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
  width: 360px !important;
  gap: 8px;
}}

.action-btn {{
  width: auto !important;
  min-width: 78px;
  height: 44px !important;
  border-radius: 999px !important;
  padding: 0 14px;
  font-size: 12px !important;
  letter-spacing: 0.03em;
}}

.btn-disagree {{
  background: var(--btn-pass-bg, #262730);
  color: var(--btn-pass-fg, #fafafa);
}}

.action-indicator {{
  font-size: 20px !important;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.25);
  color: #fff !important;
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
"""
    if _PATCH_MARKER not in css:
        css += css_append
        css_path.write_text(css, encoding="utf-8")


def load_streamlit_swipecards():
    try:
        import streamlit_swipecards as _sc
    except Exception:
        return None

    try:
        package_root = Path(_sc.__file__).resolve().parent
        _patch_frontend_files(package_root)
    except Exception:
        # Keep graceful fallback to original dependency.
        pass

    return _sc.streamlit_swipecards
