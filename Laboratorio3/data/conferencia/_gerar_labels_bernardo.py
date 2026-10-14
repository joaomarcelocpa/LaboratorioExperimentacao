"""
Script de rotulação manual — revisor B (bernardo).
Gera planilha_releases_B.csv com a coluna 'corretiva' preenchida
sem consultar a saída da heurística automática.

Critério adotado:
  True  = liberação com propósito PRIMÁRIO de corrigir bugs/falhas/regressões/
           vulnerabilidades (notas de release ou commits indicam isso claramente).
  False = liberação primariamente de novas funcionalidades, manutenção, docs,
           deps bumps, refatoração ou breaking changes sem correção de bugs.

Índice de cada linha segue a ordem do CSV (0-299).
"""
import pandas as pd

LABELS = [
    # 0  AnalogJ/scrutiny v0.8.2  — commit "fix Shoutrrr discord notification url"
    True,
    # 1  AnalogJ/scrutiny v0.8.4  — "Fix Dockerfiles in release workflow"
    True,
    # 2  AnalogJ/scrutiny v0.9.0  — primarily features + infra
    False,
    # 3  AnalogJ/scrutiny v0.9.4  — commits fix(frontend), fix(collector)
    True,
    # 4  AnalogJ/scrutiny v0.9.5  — all commits are fix(...)
    True,
    # 5  BITNP/BIThesis v3.8.6  — fix(UTE) commits
    True,
    # 6  BITNP/BIThesis v3.8.7  — style/chore only
    False,
    # 7  BITNP/BIThesis v3.8.8  — chore/docs only
    False,
    # 8  BITNP/BIThesis v3.8.10 — changelog + deps bumps
    False,
    # 9  BITNP/BIThesis v3.8.11 — changelog + chore
    False,
    # 10 CCBlueX/LiquidBounce v0.34.0 — notes and commits fix(theme)
    True,
    # 11 CCBlueX/LiquidBounce v0.35.0 — feat(InvMove) primary; mixed
    False,
    # 12 CCBlueX/LiquidBounce v0.36.0 — feat(CommandSystem) only
    False,
    # 13 CCBlueX/LiquidBounce v0.38.0 — all notes/commits are fix:
    True,
    # 14 CCBlueX/LiquidBounce v0.39.0 — Minecraft 26.2 compat / chore
    False,
    # 15 FB208/OpenBidKit_Yibiao v2.8.2 — 更健壮的数据库升级 (robustness fix)
    True,
    # 16 FB208/OpenBidKit_Yibiao v2.10.18 — GPU optimization, not a fix
    False,
    # 17 FB208/OpenBidKit_Yibiao v2.16.6 — new feature (breakpoint retry)
    False,
    # 18 FB208/OpenBidKit_Yibiao v2.19.6 — CI script update
    False,
    # 19 FB208/OpenBidKit_Yibiao v2.25.25 — 彻底解决重置任务失败 (fix reset failure)
    True,
    # 20 ImranR98/Obtainium v1.4.0 — explicit fix: change license extension
    True,
    # 21 ImranR98/Obtainium v1.6.0 — Material 3 Expressive redesign
    False,
    # 22 ImranR98/Obtainium v1.6.2 — fix: guard onNewIntent
    True,
    # 23 ImranR98/Obtainium v1.6.11 — features / translations
    False,
    # 24 ImranR98/Obtainium v1.6.16 — issue template updates, not code fix
    False,
    # 25 IrosTheBeggar/mStream v5.14.0 — fixes path traversal (security)
    True,
    # 26 IrosTheBeggar/mStream v6.1.1 — "Fix electron issues for desktop app"
    True,
    # 27 IrosTheBeggar/mStream v6.18.0 — Federation (new feature)
    False,
    # 28 IrosTheBeggar/mStream v6.21.0 — P2P Discovery binary release
    False,
    # 29 IrosTheBeggar/mStream v6.28.0 — artist catalog improvement
    False,
    # 30 Muesli-HQ/muesli v0.5.0 — first notarized release, new features
    False,
    # 31 Muesli-HQ/muesli v0.6.1 — "Fix site GitHub star link", "Fix meeting"
    True,
    # 32 Muesli-HQ/muesli v0.6.4 — new features (live Quick Note meetings)
    False,
    # 33 Muesli-HQ/muesli v0.6.9 — reliability improvements, no explicit fix
    False,
    # 34 Muesli-HQ/muesli v0.7.1 — learn from corrections (new feature)
    False,
    # 35 Portabase/portabase 1.2.4 — "🐛 Fixes" as primary section
    True,
    # 36 Portabase/portabase 1.4.5 — commits "fix: Feat/flow"
    True,
    # 37 Portabase/portabase 1.5.1 — "### 🐛 Bug Fixes" section
    True,
    # 38 Portabase/portabase 1.10.0 — "✨ Features: add firebird"
    False,
    # 39 Portabase/portabase 1.28.0 — "✨ Features: add hourly retention"
    False,
    # 40 QuiteAFancyEmerald/InvisiProxy-Legacy v6.9.3 — has fix commit
    True,
    # 41 QuiteAFancyEmerald/InvisiProxy-Legacy v6.9.4 — transport switch
    False,
    # 42 QuiteAFancyEmerald/InvisiProxy-Legacy v6.9.8 — fix: hidden history, fix: koyeb
    True,
    # 43 QuiteAFancyEmerald/InvisiProxy-Legacy v7.0.1 — has fix commit
    True,
    # 44 QuiteAFancyEmerald/InvisiProxy-Legacy v7.0.2.1 — fix: ci, fix: docker bump, fix: version
    True,
    # 45 ROCm/legacy-rocm-build rocm-7.0.2 — release notes / docs update
    False,
    # 46 ROCm/legacy-rocm-build rocm-7.1.0 — release notes / CI
    False,
    # 47 ROCm/legacy-rocm-build rocm-7.2.2 — "quality release that resolves the issue"
    True,
    # 48 ROCm/legacy-rocm-build rocm-7.2.4 — "quality release focused on performance and stability fixes"
    True,
    # 49 ROCm/legacy-rocm-build rocm-7.14.0 — architectural transition to TheRock
    False,
    # 50 Vizards/deepseek-v4-for-copilot v0.2.0 — only version bump commit
    False,
    # 51 Vizards/deepseek-v4-for-copilot v0.3.0 — new features
    False,
    # 52 Vizards/deepseek-v4-for-copilot v0.5.3 — "Bug Fixes: improve DeepSeek request failure handling"
    True,
    # 53 Vizards/deepseek-v4-for-copilot v0.8.1 — "Bug Fixes: show dynamic rates"
    True,
    # 54 Vizards/deepseek-v4-for-copilot v0.9.0 — "Features: add configurable request headers"
    False,
    # 55 Yuan-lab-LLM/ClawManager v2026.3.29 — primarily feat: commits
    False,
    # 56 Yuan-lab-LLM/ClawManager v2026.4.4 — feat: add OpenClaw resource management
    False,
    # 57 Yuan-lab-LLM/ClawManager v2026.4.21 — feat: support multiple runtime images
    False,
    # 58 Yuan-lab-LLM/ClawManager v2026.5.1 — fix: make instance deletion asynchronous
    True,
    # 59 Yuan-lab-LLM/ClawManager v2026.7.3 — peer collaboration feature
    False,
    # 60 abhinavxd/libredesk v0.9.4-beta — "## What's fixed" is the only section
    True,
    # 61 abhinavxd/libredesk v1.0.0 — both new + fix; Spanish translation is primary
    False,
    # 62 abhinavxd/libredesk v2.1.0 — omni-channel live chat (new feature)
    False,
    # 63 abhinavxd/libredesk v2.4.0 — nested filter groups, transcript download (new features)
    False,
    # 64 abhinavxd/libredesk v2.7.1 — "## What's fixed" only section
    True,
    # 65 ajayyy/SponsorBlock 6.0.2 — "Fixes for new skip profile UI"
    True,
    # 66 ajayyy/SponsorBlock 6.0.3 — "Fix skip profile menu appearing behind"
    True,
    # 67 ajayyy/SponsorBlock 6.1.3 — "Fix options page disappearing"
    True,
    # 68 ajayyy/SponsorBlock 6.1.5 — "Fix segments not skipping"
    True,
    # 69 ajayyy/SponsorBlock 6.1.6 — "Fix YouTube chapters sometimes not being shown"
    True,
    # 70 autobrr/netronome v0.8.0 — "### Bug Fixes" is primary section
    True,
    # 71 autobrr/netronome v0.9.0 — "🚀 New Features" is primary
    False,
    # 72 autobrr/netronome v0.13.0 — "New Features" primary
    False,
    # 73 autobrr/netronome v0.14.1 — Maintenance + refactor
    False,
    # 74 autobrr/netronome v0.15.0 — has explicit "Bug Fixes" section
    True,
    # 75 benavlabs/FastAPI-boilerplate v0.15.0 — "bugfix: ensure user lookup" commit
    True,
    # 76 benavlabs/FastAPI-boilerplate v0.16.0 — type safety improvements (feature)
    False,
    # 77 benavlabs/FastAPI-boilerplate v0.17.0 — "Final Polish Before the Rebuild"
    False,
    # 78 benavlabs/FastAPI-boilerplate v0.18.0 — "The Pluggable Restructure"
    False,
    # 79 benavlabs/FastAPI-boilerplate v0.19.0 — crudauth Migration
    False,
    # 80 benjamimgois/goverlay 1.6.9 — "fix: sync original_dlls array"
    True,
    # 81 benjamimgois/goverlay 1.8.0 — complete visual overhaul (feature)
    False,
    # 82 benjamimgois/goverlay 1.8.2 — notes: "new features e bug fixes"; fix commits
    True,
    # 83 benjamimgois/goverlay 1.8.8 — "Fixed deadlock" prominent in notes
    True,
    # 84 benjamimgois/goverlay 1.9.0 — notes mention "fixes"; fix commit present
    True,
    # 85 bevyengine/bevy v0.17.1 — "A full diff of what's been fixed"
    True,
    # 86 bevyengine/bevy v0.17.2 — "A full diff of what's been fixed"
    True,
    # 87 bevyengine/bevy v0.17.3 — "A full diff of what's been fixed"; fix commits
    True,
    # 88 bevyengine/bevy v0.18.1 — fix commits predominant
    True,
    # 89 bevyengine/bevy v0.19.0 — major feature release
    False,
    # 90 browserless/browserless v2.51.2 — "### Bug Fixes" only section
    True,
    # 91 browserless/browserless v2.54.2 — "### Bug Fixes" primary
    True,
    # 92 browserless/browserless v2.55.0 — "### Features" primary
    False,
    # 93 browserless/browserless v2.56.1 — "### Bug Fixes" only
    True,
    # 94 browserless/browserless v2.56.3 — "### Bug Fixes" only
    True,
    # 95 bucket4j/bucket4j 8.16.0 — "feat: add retry strategy" primary
    False,
    # 96 bucket4j/bucket4j 8.16.1 — only version update commit
    False,
    # 97 bucket4j/bucket4j 8.17.0 — multiple fix commits (Fix Export-Package, fix docs)
    True,
    # 98 bucket4j/bucket4j 8.19.0 — "Support backoff in CAS retry" (feature)
    False,
    # 99 bucket4j/bucket4j 8.20.0 — "fix argument checking"; "fix documentation issues"
    True,
    # 100 clientIO/joint v4.2.0 — new ELK layout example (feature)
    False,
    # 101 clientIO/joint v4.2.5 — "fix to guard merge() against prototype pollution" (security)
    True,
    # 102 clientIO/joint @joint/core@4.3.2 — Patch Changes but chore/maintenance
    False,
    # 103 clientIO/joint @joint/react@4.3.4 — "fix events dispatched at paper container"
    True,
    # 104 clientIO/joint @joint/react@4.3.5 — "fix links connected to other links"
    True,
    # 105 cloudflare/quiche 0.24.6 — new Config method (feature)
    False,
    # 106 cloudflare/quiche 0.26.0 — Breaking Changes + new features
    False,
    # 107 cloudflare/quiche 0.29.0 — Breaking Changes + removal
    False,
    # 108 cloudflare/quiche 0.29.1 — "Fixed bandwidth calculation"
    True,
    # 109 cloudflare/quiche 0.29.3 — "⚠️ Security: Fixed unbounded PathEvent queue growth"
    True,
    # 110 connorgallopo/Tracearr v1.2.0 — "fix: use expo-github-action@main to resolve cache issues"
    True,
    # 111 connorgallopo/Tracearr v1.4.7 — "Couple performance tweaks"
    False,
    # 112 connorgallopo/Tracearr v1.4.8 — nav update
    False,
    # 113 connorgallopo/Tracearr v1.4.22 — "Bugfixes for session tracking, notification webhooks"
    True,
    # 114 connorgallopo/Tracearr v2.1.0 — Live Stats feature
    False,
    # 115 dbos-inc/dbos-transact-py 2.14.0 — "Fix Authentication & Authorization" present
    True,
    # 116 dbos-inc/dbos-transact-py 2.16.0 — features only
    False,
    # 117 dbos-inc/dbos-transact-py 2.22.0 — features only
    False,
    # 118 dbos-inc/dbos-transact-py 2.25.0 — "Fix Destroy Hang" as first item
    True,
    # 119 dbos-inc/dbos-transact-py 2.27.0 — features/migration
    False,
    # 120 developmentseed/titiler 0.24.1 — new grayscale/bitonal algorithms
    False,
    # 121 developmentseed/titiler 1.1.1 — "fix: make sure TMS have ids in WMTS response"
    True,
    # 122 developmentseed/titiler 2.0.0 — major version, new features
    False,
    # 123 developmentseed/titiler 2.0.5 — "fix: titiler-xarray | add httpx dependency"
    True,
    # 124 developmentseed/titiler 2.1.1 — "fix(#1455): correct type annotation issue"
    True,
    # 125 dicebear/dicebear v9.3.0 — Fix style preview links, Fix artist name
    True,
    # 126 dicebear/dicebear v9.4.0 — "Security: ensureSize() no longer reads SVG's width/height"
    True,
    # 127 dicebear/dicebear v10.3.0 — new Dart library (feature)
    False,
    # 128 dicebear/dicebear v10.5.0 — "quiet" release with fix commits
    True,
    # 129 dicebear/dicebear v10.6.0 — new styles (features)
    False,
    # 130 django-cms/django-cms 5.0.4 — "fix: Wrong placeholders rendered"
    True,
    # 131 django-cms/django-cms 5.0.5 — "fix: Searching pages for language-specific content failed"
    True,
    # 132 django-cms/django-cms 4.1.11 — "fix: Chunk size was missing"
    True,
    # 133 django-cms/django-cms 5.1.1 — deps bumps only
    False,
    # 134 django-cms/django-cms 5.1.3 — "fix: inline editing modals", "fix: Migration 0045"
    True,
    # 135 doctrine/DoctrineBundle 2.17.0 — "Feature release (minor)"
    False,
    # 136 doctrine/DoctrineBundle 3.1.1 — "3.1.x bugfix release (patch)"
    True,
    # 137 doctrine/DoctrineBundle 3.2.2 — "Fixes possible 3.2.0 BC break"
    True,
    # 138 doctrine/DoctrineBundle 3.2.5 — "3.2.x bugfix release (patch)"
    True,
    # 139 doctrine/DoctrineBundle 3.2.6 — Revert commit (corrective by nature)
    True,
    # 140 drhelius/Gearboy 3.7.4 — "🐛 Bug fixes" noted
    True,
    # 141 drhelius/Gearboy 3.7.5 — "🐛 Bug fixes"; "Fix Windows build"
    True,
    # 142 drhelius/Gearboy 3.8.3 — "🐛 Many bug fixes"
    True,
    # 143 drhelius/Gearboy 3.8.6 — "🐛 Many bug fixes and improvements"; fix commits
    True,
    # 144 drhelius/Gearboy 3.8.9 — "🐛 Many bug fixes and improvements"; Fix Rom Info colors
    True,
    # 145 ebullient/obsidian-admonition 11.0.0 — "Fixes:" section; 🐛 Fix suggested
    True,
    # 146 ebullient/obsidian-admonition 11.0.4 — "Fixes: 🐛 Register sentence case handler"
    True,
    # 147 ebullient/obsidian-admonition 12.0.3 — style/docs changes only
    False,
    # 148 ebullient/obsidian-admonition 12.0.4 — API update, no fix
    False,
    # 149 ebullient/obsidian-admonition 12.0.6 — "Fixes: 🐛 avoid hierarchy error w/ suggester"
    True,
    # 150 flix/flix v0.65.0 — primarily features; fix commit present but minor
    False,
    # 151 flix/flix v0.69.0 — features only
    False,
    # 152 flix/flix v0.69.3 — "fix: resolve effect declarations in DefCompleter"
    True,
    # 153 flix/flix v0.74.0 — fix: AssocType hashCode, fix: source equals + perf
    True,
    # 154 flix/flix v0.76.2 — refactor only
    False,
    # 155 guillaumemeyer/watermarks-remover v0.1.0 — packaging polish (not a fix)
    False,
    # 156 guillaumemeyer/watermarks-remover v0.2.0 — "Bug-fix release" explicitly
    True,
    # 157 guillaumemeyer/watermarks-remover v0.3.0 — new SynthID scoring feature
    False,
    # 158 guillaumemeyer/watermarks-remover v0.5.0 — "biggest release yet: full service"
    False,
    # 159 guillaumemeyer/watermarks-remover v0.7.0 — Layer B rewrite (feature)
    False,
    # 160 helm-unittest/helm-unittest v1.0.2 — replacement of yaml library (maintenance)
    False,
    # 161 helm-unittest/helm-unittest v1.0.3 — "Fixes: Corrected newlines"
    True,
    # 162 helm-unittest/helm-unittest v1.1.0 — has explicit "Fixes" section
    True,
    # 163 helm-unittest/helm-unittest v1.1.1 — Improvements/Updates, no fix section
    False,
    # 164 helm-unittest/helm-unittest v1.1.2 — "Fixes: Fix handling multiline block scalars"
    True,
    # 165 hyperledger/fabric v3.1.2 — "Improvements and Fixes" section
    True,
    # 166 hyperledger/fabric v2.5.14 — "updates code dependencies"
    False,
    # 167 hyperledger/fabric v3.1.3 — "Improvements and Fixes"
    True,
    # 168 hyperledger/fabric v3.1.4 — "Fixed working with Docker Engine v29+"
    True,
    # 169 hyperledger/fabric v2.5.16 — "Fixes: Fixed recover from panic in HandleTransaction"
    True,
    # 170 ixartz/Next-js-Boilerplate v5.1.12 — "### Bug Fixes" section
    True,
    # 171 ixartz/Next-js-Boilerplate v6.0.5 — "### Bug Fixes" section
    True,
    # 172 ixartz/Next-js-Boilerplate v6.1.0 — "Features: add local postgres database"
    False,
    # 173 ixartz/Next-js-Boilerplate v6.3.1 — "### Bug Fixes: enable noUncheckedSideEffectImports"
    True,
    # 174 ixartz/Next-js-Boilerplate v6.3.5 — "### Bug Fixes: render user profile only for signed-in"
    True,
    # 175 jackocnr/intl-tel-input v26.0.3 — "Fix: missing globe icon when showFlags=false"
    True,
    # 176 jackocnr/intl-tel-input v26.7.3 — "fix: useFullscreenPopup disabled on mobile"
    True,
    # 177 jackocnr/intl-tel-input v27.2.1 — "Fix: file extensions on imports in generated files"
    True,
    # 178 jackocnr/intl-tel-input v29.0.5 — "Update utils to libphonenumber v9.0.32" (update)
    False,
    # 179 jackocnr/intl-tel-input v29.5.0 — "Add a close button" (new feature)
    False,
    # 180 kevin1024/vcrpy v8.0.0 — "Breaking Changes" + new features
    False,
    # 181 kevin1024/vcrpy v8.1.0 — "## Bug Fixes" section present
    True,
    # 182 kevin1024/vcrpy v8.1.1 — "Fix sync requests in async contexts for HTTPX"
    True,
    # 183 kevin1024/vcrpy v8.2.1 — "SECURITY: Cassettes now loaded with safe YAML loader"
    True,
    # 184 kevin1024/vcrpy v8.3.0 — "Add support for niquests" (feature)
    False,
    # 185 layui/layui v2.12.1 — all commits are fix(...)
    True,
    # 186 layui/layui v2.13.1 — fix commits present
    True,
    # 187 layui/layui v2.13.4 — fix commits present
    True,
    # 188 layui/layui v2.13.8 — predominantly fix commits
    True,
    # 189 layui/layui v2.13.9 — fix commits + one feat
    True,
    # 190 lexmount/moli v0.1.1 — "Fix legacy center", "Fix intrinsic image sizing", multiple fixes
    True,
    # 191 lexmount/moli v1.0.5 — "fix(renderer): block javascript URLs" in notes
    True,
    # 192 lexmount/moli v1.0.6 — primarily feat(fetch) new features
    False,
    # 193 lexmount/moli v1.1.5 — "fix(xhr): resolve open UR" and fix commits
    True,
    # 194 lexmount/moli v1.1.7 — all notes entries are fix(...)
    True,
    # 195 locustio/locust 2.41.3 — new feature primary; "Make workers correctly ignore" is a fix
    False,
    # 196 locustio/locust 2.42.5 — "Log when otel is enabled" (not a fix)
    False,
    # 197 locustio/locust 2.42.6 — "Fix Toml Parser Being Called on..."
    True,
    # 198 locustio/locust 2.46.0 — "fix: proper_round gives wrong result"
    True,
    # 199 locustio/locust 2.46.4 — "Fix FastHttpUser streaming response_length"
    True,
    # 200 lotus-data/lotus v1.1.4 — Delete .idea folder + new features
    False,
    # 201 lotus-data/lotus v1.2.0 — "inconsistent sem_extract output fix" as first item
    True,
    # 202 lotus-data/lotus v1.2.1 — "Fix pairwise_judge GEPA helper-instruction tests"
    True,
    # 203 lotus-data/lotus v1.2.3 — "Agentic map-reduce" (new feature)
    False,
    # 204 lotus-data/lotus v1.2.4 — docs only
    False,
    # 205 meriyah/meriyah v7.1.0 — "Features: add isParseError()" primary
    False,
    # 206 meriyah/meriyah v7.1.1 — "## Bug Fixes" section
    True,
    # 207 meriyah/meriyah v7.1.2 — "### Bug Fixes: reject empty unicode code point escape"
    True,
    # 208 meriyah/meriyah v7.3.1 — "### Bug Fixes: forbid } and > in JSX element children"
    True,
    # 209 meriyah/meriyah v7.3.3 — "### Bug Fixes: count line terminators and decode entities"
    True,
    # 210 mhogomchungu/media-downloader 5.4.3 — "always respect max concurrent operations"
    False,
    # 211 mhogomchungu/media-downloader 5.4.4 — "code improvement" only
    False,
    # 212 mhogomchungu/media-downloader 5.4.8 — "fix a bug when running on windows7"
    True,
    # 213 mhogomchungu/media-downloader 5.6.1 — code improvements, no explicit bug fix
    False,
    # 214 mhogomchungu/media-downloader 5.6.5 — update how to read yt-dlp data
    False,
    # 215 microsoft/monaco-editor v0.54.0 — "Fixes microsoft logo" among changes
    True,
    # 216 microsoft/monaco-editor v0.55.0 — "Fixes npx playwright", "Fixes issue #5113"
    True,
    # 217 microsoft/monaco-editor v0.55.1 — "Fixes missing language exports"
    True,
    # 218 microsoft/monaco-editor v0.56.0 — dep bumps + "Removes left..." (not a fix)
    False,
    # 219 microsoft/monaco-editor v0.57.0 — release preparation with dep bumps
    False,
    # 220 nodemailer/nodemailer v7.0.11 — "Bug Fixes: prevent stack overflow DoS"
    True,
    # 221 nodemailer/nodemailer v8.0.1 — "Bug Fixes: absorb TLS errors during socket teardown"
    True,
    # 222 nodemailer/nodemailer v8.0.6 — "Bug Fixes: restore base64 wrap() trim behavior"
    True,
    # 223 nodemailer/nodemailer v9.0.6 — "Bug Fixes: recover the addr-spec from angle-addr"
    True,
    # 224 nodemailer/nodemailer v9.1.0 — "Features: cap recipients per message" primary
    False,
    # 225 nolabs-ai/nono v0.2.3 — bug-19 PR merged; "usr-local-fix" PR
    True,
    # 226 nolabs-ai/nono v0.3.1 — deps bumps only
    False,
    # 227 nolabs-ai/nono v0.44.0 — "fix(wiring): harden install and uninstall wiring"; "fix(package)"
    True,
    # 228 nolabs-ai/nono v0.54.0 — deps bumps/features
    False,
    # 229 nolabs-ai/nono v0.60.0 — "fix: correct Quick Start profile reference"; "fix(proxy)"
    True,
    # 230 ocaml/merlin v5.6-503 — "Fix merlin_reader for OpenBSD"
    True,
    # 231 ocaml/merlin v5.6-504 — same changelog with Fix sections
    True,
    # 232 ocaml/merlin v5.7.0-504 — "Implement new refactor-extract-region command" (feature)
    False,
    # 233 ocaml/merlin v5.8-505 — "Fix signature-help with type aliases", "Fix locate on punned"
    True,
    # 234 ocaml/merlin v5.8.1-505 — "fix files modified since the index was built"
    True,
    # 235 openiddict/openiddict-core 7.2.0 — .NET 10 support (feature)
    False,
    # 236 openiddict/openiddict-core 7.3.0 — Mutual TLS authentication (new feature)
    False,
    # 237 openiddict/openiddict-core 7.4.0 — mTLS feature continuation
    False,
    # 238 openiddict/openiddict-core 7.6.1 — "GitHub web provider was fixed to support the iss parameter"
    True,
    # 239 openiddict/openiddict-core 7.7.1 — "identity token principal correctly restored"
    True,
    # 240 rhysd/actionlint v1.7.8 — new `models` permission support (feature)
    False,
    # 241 rhysd/actionlint v1.7.9 — Add support for ubuntu-slim runner (feature)
    False,
    # 242 rhysd/actionlint v1.7.10 — Support YAML anchors and aliases (feature)
    False,
    # 243 rhysd/actionlint v1.7.11 — Support case() function (feature)
    False,
    # 244 rhysd/actionlint v1.7.12 — Support timezone configuration (feature)
    False,
    # 245 rohitg00/pro-workflow v1.1.0 — new /commit command (feature)
    False,
    # 246 rohitg00/pro-workflow v1.2.0 — Scout Agent new feature
    False,
    # 247 rohitg00/pro-workflow v3.1.0 — decision framework feature
    False,
    # 248 rohitg00/pro-workflow v3.3.0 — wiki knowledge base feature
    False,
    # 249 rohitg00/pro-workflow v3.4.0 — "fix(hooks): read documented payload fields" in notes
    True,
    # 250 safing/portmaster v2.1.7 — notes mention bug fixes alongside new features
    True,
    # 251 safing/portmaster v2.1.18 — "Packet injection fixes", "Fixed BSODs"
    True,
    # 252 safing/portmaster v2.1.19 — "fix: Mitigate CWE-428 unquoted service path" (security)
    True,
    # 253 safing/portmaster v2.2.1 — Split Tunneling new feature
    False,
    # 254 safing/portmaster v2.2.3 — "fix: Oversized DNS packets could kill the DNS listener"
    True,
    # 255 sei-protocol/sei-chain v6.1.12 — "Fix tx sender calculation for RPCs"
    True,
    # 256 sei-protocol/sei-chain v6.1.13 — "Return meaningful error instead of malformed data"
    True,
    # 257 sei-protocol/sei-chain v6.3.1 — "default SSTORE value back to original 20k"; "fix: support iavl"
    True,
    # 258 sei-protocol/sei-chain v6.4.2 — "Receipt Pruning Fix: bug introduced in v6.4.0"
    True,
    # 259 sei-protocol/sei-chain v6.4.4 — improvement for gas price reporting
    False,
    # 260 skrub-data/skrub 0.7.0 — "Data Ops can now be tuned with Optuna" (feature)
    False,
    # 261 skrub-data/skrub 0.7.1 — "New features: fetch_california_housing()"
    False,
    # 262 skrub-data/skrub 0.7.2 — "squashed more bugs"
    True,
    # 263 skrub-data/skrub 0.9.0 — features only
    False,
    # 264 skrub-data/skrub 0.10.0 — new transformers (feature)
    False,
    # 265 sunpy/sunpy v7.0.3 — "Fix GONGMagnetogramMap for correct DATE-OBS"
    True,
    # 266 sunpy/sunpy v7.0.4 — "## Bug Fixes: Fix ADAPTClient returning no results"
    True,
    # 267 sunpy/sunpy v7.1.0 — Breaking Changes + new features
    False,
    # 268 sunpy/sunpy v7.0.5 — "## Bug Fixes: Fixed a bug in sunpy.coordinates.spice"
    True,
    # 269 sunpy/sunpy v8.0.0 — major release
    False,
    # 270 the-open-agent/openagent v1.685.2 — "### Bug Fixes: support RMM scan provider"
    True,
    # 271 the-open-agent/openagent v1.693.1 — "### Bug Fixes" multiple fixes
    True,
    # 272 the-open-agent/openagent v1.718.1 — "### Bug Fixes: fix error format"
    True,
    # 273 the-open-agent/openagent v1.784.0 — "fix Dockerfile Node.js CI error" (labeled feat)
    True,
    # 274 the-open-agent/openagent v1.796.0 — "### Bug Fixes: remove crowdin"
    True,
    # 275 thingsboard/thingsboard v4.2.1 — "Minor release with bug fixes and improvements"
    True,
    # 276 thingsboard/thingsboard v4.2.1.1 — "Patch release with bug fixes"
    True,
    # 277 thingsboard/thingsboard v4.3.1.1 — "### Security: Fixed XSS vulnerability"
    True,
    # 278 thingsboard/thingsboard v4.2.2.5 — "### Security: Fixed CVE-..."
    True,
    # 279 thingsboard/thingsboard v4.2.2.6 — "### Security: Fixed CVE-..."
    True,
    # 280 thomiceli/opengist v1.12.0 — "### Added" features only
    False,
    # 281 thomiceli/opengist v1.12.1 — "### Fixed" section; fix commits
    True,
    # 282 thomiceli/opengist v1.14.0 — "### Added" features primarily
    False,
    # 283 thomiceli/opengist v1.15.1 — "### Fixed" is the only section
    True,
    # 284 thomiceli/opengist v1.15.2 — "### Fixed: Prevent writes through symbolic links"
    True,
    # 285 tonquer/JMComic-qt v1.3.0 — 修复 (fix) items are primary in notes
    True,
    # 286 tonquer/JMComic-qt v1.3.2 — 修复图片可能下载损坏 (fix images download corrupt)
    True,
    # 287 tonquer/JMComic-qt v1.3.3 — 修复nosr无法看图 (fix nosr unable to view images)
    True,
    # 288 tonquer/JMComic-qt v1.3.5 — 修复网络差时出现闪退卡死 (fix crash/freeze)
    True,
    # 289 tonquer/JMComic-qt v1.3.6 — 修复本地漫画翻页错误 (fix page-turning error)
    True,
    # 290 tqdm/tqdm v4.67.2 — "fix format_interval for negative numbers"
    True,
    # 291 tqdm/tqdm v4.68.0 — "fix contrib.{discord,telegram} error handling"
    True,
    # 292 tqdm/tqdm v4.68.3 — maintenance/features, no prominent fix
    False,
    # 293 tqdm/tqdm v4.70.0 — "fix total based on shortest iterable length"
    True,
    # 294 tqdm/tqdm v4.70.1 — "fix no-len iterables"
    True,
    # 295 waf/CSharpRepl v0.8.0 — new inspect feature
    False,
    # 296 waf/CSharpRepl v0.8.1 — new config file location behavior
    False,
    # 297 waf/CSharpRepl v0.9.0 — "Live method replacement" (new feature)
    False,
    # 298 waf/CSharpRepl v0.9.1 — "Simple variable declarations no longer require semicolon"
    False,
    # 299 waf/CSharpRepl v0.9.2 — "Breaking: rename inspect command to connect"
    False,
]

assert len(LABELS) == 300, f"Expected 300 labels, got {len(LABELS)}"

df = pd.read_csv("planilha_releases.csv")
assert len(df) == 300

df["corretiva"] = LABELS
out = "planilha_releases_B.csv"
df.to_csv(out, index=False)

true_count = sum(LABELS)
print(f"Rotulação concluída: {true_count} True ({true_count/300:.1%}), "
      f"{300 - true_count} False ({(300 - true_count)/300:.1%})")
print(f"Arquivo salvo: {out}")
