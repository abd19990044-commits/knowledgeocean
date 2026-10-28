/**
 * Knowledge Ocean - Modern Interactive SPA Engine
 * Pure Vanilla ES6 + React 18 + HTM (Zero Babel Overhead, 100% Offline Ready)
 */

(function () {
  const { useState, useEffect, useRef, useMemo } = React;
  const html = htm.bind(React.createElement);

  // Citation helpers
  function apaToHtmlFormatted(text) {
    if (!text) return "";
    let h = String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    h = h.replace(/\*\*([^*]+)\*\*/g, '<b style="font-weight: bold;">$1</b>');
    h = h.replace(/\*([^*]+)\*/g, '<i style="font-style: italic;">$1</i>');
    h = h.replace(/(https?:\/\/doi\.org\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" style="color: #0563C1; text-decoration: underline;">$1</a>');
    return `<p style="font-family: 'Times New Roman', Times, serif; font-size: 14pt; color: #000000; line-height: 1.5; margin: 0; padding: 0;">${h}</p>`;
  }

  function apaToPlainText(text) {
    if (!text) return "";
    return String(text)
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1");
  }

  function generateAPA(p) {
    if (p && p.apa) return p.apa;
    const authors = (p.authors && p.authors.length) ? p.authors.slice(0, 7).join(", ") : "Unknown";
    const year = (p.year && p.year !== "0000") ? `(${p.year})` : "(n.d.)";
    const title = p.title ? p.title.trim().replace(/\.$/, "") + "." : "No Title.";
    
    let journalClause = "";
    if (p.journal) {
      journalClause = ` *${p.journal.trim()}*`;
      const vol = p.volume ? String(p.volume).replace(/^(?:vol(?:ume|\.)?\s*)/i, "").trim() : "";
      let iss = (p.issue || p.number) ? String(p.issue || p.number).replace(/^[()]+|[()]+$/g, "").trim() : "";
      iss = iss.replace(/^(?:(?:issue|no|number|\.)\s*)/i, "").trim();
      let pgs = (p.pages || p.page || p.article_number || p.article_no) ? String(p.pages || p.page || p.article_number || p.article_no).trim() : "";
      pgs = pgs.replace(/^(?:pp?\.?\s*)/i, "").replace(/[-–—]+/g, "–").trim();

      if (vol) {
        journalClause += `, **${vol}**`;
        if (iss) journalClause += `(${iss})`;
      } else if (iss) {
        journalClause += `, (${iss})`;
      }
      if (pgs) {
        journalClause += `, ${pgs}`;
      }
      journalClause += ".";
    }
    const doi = p.doi && p.doi !== "N/A" ? ` https://doi.org/${p.doi}` : (p.oa_url ? ` ${p.oa_url}` : "");
    return `${authors} ${year}. ${title}${journalClause}${doi}`.trim();
  }

  function generateBibTeX(p) {
    if (p && p.bibtex) return p.bibtex;
    const firstAuthor = (p.authors && p.authors.length) ? p.authors[0].split(" ").pop().toLowerCase() : "unknown";
    const year = p.year || "2026";
    const cleanTitle = (p.title || "paper").replace(/[^a-zA-Z0-9]/g, "").slice(0, 10).toLowerCase();
    const citeKey = `${firstAuthor}${year}${cleanTitle}`;
    const authorsStr = (p.authors && p.authors.length) ? p.authors.join(" and ") : "Unknown";
    let bib = `@article{${citeKey},\n`;
    bib += `  title = {${p.title || "No Title"}},\n`;
    bib += `  author = {${authorsStr}},\n`;
    if (p.journal) bib += `  journal = {${p.journal}},\n`;
    if (p.year && p.year !== "0000") bib += `  year = {${p.year}},\n`;
    if (p.doi) bib += `  doi = {${p.doi}},\n`;
    if (p.oa_url) bib += `  url = {${p.oa_url}},\n`;
    bib += `}`;
    return bib;
  }


  // =========================================================================
  // Internationalization (i18n): English (Default) & Arabic
  // Application Name: Knowledge Ocean (English Only)
  // =========================================================================
  const I18N = {
    en: {
      appName: "Knowledge Ocean",
      appVersion: "v1.0",
      subtitle: "High-Precision Academic Retrieval & Documentation System",
      developerCredit: "Developed by ABDULSALAM S. HASAN",
      vipUnlimitedBadge: "✨ VIP Access Active (Unlimited Searches)",
      quotaBadgeText: "Guest Quota: 50 Searches (Renews 12:00 AM Baghdad time)",
      quotaExhaustedAlert: "Daily search quota reached (50 standard searches or 25 with summaries). Quota renews automatically at 12:00 AM Baghdad time (UTC+3), or enter a VIP access key.",

      offlineBadge: "Standalone Local Edition (Offline Ready)",
      downloadLocalZip: "Download Local Edition (ZIP)",
      downloadLocalZipTitle: "Download local edition for offline standalone execution on your machine",
      settingsBtn: "Settings & Sources",
      settingsTitle: "Researcher settings and academic sources",
      themeDarkTooltip: "Switch to Dark Mode",
      themeLightTooltip: "Switch to Light Mode",
      langSwitchTooltip: "التبديل إلى اللغة العربية (Switch to Arabic)",
      langTargetLabel: "AR",

      // Nav Tabs
      tabExplorer: "Comprehensive Academic Explorer",
      tabDoiHub: "DOI & Citation Resolver",
      instantLookupBadge: "Instant Lookup",

      // DOI Hub Header
      doiHubTitle: "DOI & Academic Citation Resolver",
      doiHubSubtitle: "Lookup, verify, and resolve scholarly metadata via Digital Object Identifier (DOI) or match paper titles to verified citations with instant APA / BibTeX generation.",
      returnToExplorer: "Return to Academic Explorer",
      doiSubtabDirect: "Direct DOI Lookup",
      doiSubtabTitle: "Match Title to DOI",

      // DOI Direct Tab
      doiInputLabel: "Enter direct DOI or full link (https://doi.org/...)",
      doiInputPlaceholder: "e.g. 10.1007/s40278-024-60584-4 or https://doi.org/10.1186/s13256-025-05459-w",
      doiLookupBtn: "Lookup & Verify 🔍",
      doiLookupLoading: "Looking up DOI...",
      doiExamplesLabel: "Sample DOIs for quick test:",
      peerReviewed: "Peer-Reviewed",
      preprint: "Preprint",
      openAccess: "Open Access",
      citationsCount: "citations",
      sourcesLabel: "Sources:",
      publisherSubNotice: "(Publisher subscription required — official link available above)",
      downloadFullOa: "📥 Download / Read Full Paper (Open Access)",
      scihubConfirmedBtn: "Alternative Repository (Sci-Hub)",
      scihubSearchBtn: "Search in Sci-Hub",
      scihubSearchTitle: "Search for paper on Sci-Hub repository",
      rgDownloadBtn: "📥 Available for Download (ResearchGate)",
      rgSearchBtn: "Search in ResearchGate",
      rgSearchTitle: "Search and verify publication on ResearchGate platform",
      copyApaBtn: "Copy APA 7th",
      copyBibtexBtn: "Copy BibTeX",
      copyRisBtn: "Copy RIS",
      copiedApaAlert: "APA 7th citation copied successfully",
      copiedBibtexAlert: "BibTeX citation copied successfully",
      copiedRisAlert: "RIS citation copied successfully",

      // DOI Title Tab
      titleInputLabel: "Enter full paper title to extract DOI and metadata",
      titleInputPlaceholder: "e.g. Determination of ibuprofen and naproxen in tablets with serious dye interferences...",
      titleFindBtn: "Extract DOI 🔍",
      titleFindLoading: "Searching academic databases...",
      titleMatchHeader: "Verified matching papers found:",
      detailedCheckBtn: "🔍 Detailed Check",
      searchRgTitle: "Search on ResearchGate",
      searchScihubTitle: "Search on Sci-Hub",

      // Explorer Top Banners
      localBannerText: "⚡ Running in Standalone Local Environment — PDF files are saved directly to your computer without external dependencies.",
      cloudBannerTitle: "Run Knowledge Ocean locally on your PC",
      cloudBannerBadge: "Full Standalone Version",
      cloudBannerDesc: "Download the portable package and run the server with one click via run_local.bat for fast searching and direct local saving.",
      cloudBannerBtn: "Download Local Package (ZIP) ↓",

      // Search Form
      searchSettingsTitle: "Comprehensive Academic Search & Settings",
      localFullBadge: "Local Full Edition (Unlimited Discovery & Extraction)",
      cloudQuotaBadge: "Cloud Usage (50 papers with full index)",
      operationModeLabel: "Operation Mode",
      localAccessText: "Full Open Local Access (No Key Needed)",
      historyBtn: "Search History ◫",
      historyBtnLoading: "Loading...",
      accessKeyLabel: "Access Key (VIP)",
      accessKeyPlaceholder: "Enter VIP access key for unlimited search...",
      searchModeLabel: "Search Mode",
      modeKeyword: "Keywords & Boolean (AND, OR, NOT)",
      modeAuthor: "Author Name (Author Mode)",
      modeExact: "Exact Phrase Match",
      modeDoi: "🎯 Direct DOI Lookup (Jump to DOI Hub ↗)",
      modeTitleDoi: "📑 Match Title to DOI (Jump to DOI Hub ↗)",
      queryLabel: "Search Query (Keywords / Topics / Authors)",
      clearQueryBtn: "Clear Query ✕",
      queryPlaceholder: "Enter research topic, keywords, paper title, or author name...",
      exampleQueriesLabel: "Quick search suggestions:",

      // Advanced Filters
      strictTitleLabel: "Strict Title Filter (Title Must Filter)",
      strictTitlePrecisionBadge: "99% Precision",
      strictTitleDesc: "Choose whether search keywords must appear strictly in the paper title, or across both title and abstract.",
      strictTitleOnBadge: "ON - Strict Title Matching",
      strictTitleOnText: "Strictly excludes any paper whose title does not contain your keywords. Ensures 99% topic precision by scanning deep database batches until your requested paper count is met or repositories are exhausted. (Recommended for exact topics or specific queries).",
      strictTitleOffBadge: "OFF - Smart Comprehensive Search (Default)",
      strictTitleOffText: "Searches across both titles and abstracts to ensure no relevant study is missed, automatically prioritizing papers matching terms in their titles at the top. (Recommended for broad academic discovery and full literature coverage).",
      timeRangeLabel: "Time Range (Publication Years)",
      yearFromPlaceholder: "From (e.g. 2020)",
      yearToPlaceholder: "To (e.g. 2026)",
      yearPresetRange: "2020 - 2026",
      yearPresetNow: "Current Year Only",
      yearPresetAll: "All Years",
      maxResultsLabel: "Maximum Results",
      limit5: "5 Papers",
      limit10: "10 Papers",
      limit25: "25 Papers",
      limit50: "50 Papers",
      limit100: "100 Results",
      limit250: "250 Results",
      limitAll: "Comprehensive (Everything Found)",
      dbSourcesLabel: "Databases & Sources",
      sourceAll: "All Engines (12 Open Science Engines)",
      sourcePubmed: "PubMed (Biomedical & Life Sciences)",
      sourceElsevierLocal: "Scopus (Elsevier)",
      sourceElsevierCloud: "Scopus (Elsevier) [Requires VIP Key]",
      sourceEuropepmc: "Europe PMC",
      sourceOpenalex: "OpenAlex (Global Scientific Graph)",
      sourceCrossref: "Crossref (Official DOIs)",
      sourceSemantic: "Semantic Scholar (AI Knowledge Graph)",
      sourceDoaj: "DOAJ (Directory of Open Access Journals)",
      sourceCore: "CORE (Open Access Repositories)",
      sourceZenodo: "Zenodo (CERN / Open Access)",
      sourceBooks: "Book Repositories (Google Books, Open Library)",
      preprintsLabel: "Preprints",
      includePreprintsText: "Include preprints (arXiv, bioRxiv, OpenAlex, etc.)",
      affiliationLabel: "Institutional Affiliation (Optional - Match University or Center)",
      affiliationPlaceholder: "e.g. Harvard University, Oxford, MIT, University of Mosul...",
      fulltextScrapingLabel: "Download Full-Text Papers (PDF Scraping)",
      fulltextScrapingBadge: "Advanced Optional Feature",
      fulltextScrapingDesc: "Includes comprehensive scholarly abstracts in search results and PDF reports",
      fulltextWarningTitle: "Time Consumption Notice:",
      fulltextWarningText: "Downloading full papers takes extra time depending on publisher servers and volume.",
      fulltextQualityBadge: "Academic Quality Guarantee: Only verified academic PDF files (%PDF) are saved.",
      fulltextDisabledNote: "Disabled by default for fast searching and instant abstract generation in seconds.",
      startSearchBtn: "Start Academic Search 🔍",
      searchingBtn: "Searching...",
      cancelSearchBtn: "Cancel",

      // Results Section
      retrievedHeader: "Retrieved Research Papers & Studies",
      papersRetrievedCount: "papers retrieved",
      filterAll: "All Papers",
      filterPeer: "Peer-Reviewed",
      filterPreprints: "Preprints",
      filterOa: "Open Access",
      filterResultsPlaceholder: "Filter current results (by title, journal, author, DOI)...",
      downloadResultsZip: "Download Results (ZIP)",
      viewResultsFile: "View File",
      directLinkDownload: "↗ Direct Link / Download",
      checkingAvailability: "Checking availability...",
      freeOaDownload: "📥 Free Download (Open Access)",
      publisherSubscription: "🔒 Publisher Subscription",
      checkFreeAccessBtn: "🔍 Check Free Access",
      badgeAvailable: "Available",
      badgeDownload: "Download",
      copyDoiLinkBtn: "📋 Copy DOI Link",
      copyDoiLinkDone: "✓ Link Copied",
      readAbstractBtn: "Read Abstract",
      hideAbstractBtn: "Hide Abstract",
      noAbstractText: "No abstract text available for this paper in open metadata.",

      // Modals
      abstractModalTitle: "Research Abstract",
      copyAbstractBtn: "📋 Copy Abstract",
      copyAbstractDone: "✓ Copied",
      modalCloseBtn: "Close",
      downloadCompleteTitle: "Search & Compilation Completed",
      downloadCompleteDesc: "Comprehensive academic dossier generated and ready for exploration.",
      downloadPackageBtn: "📥 Download Package",
      viewFileBtn: "👁 View Results File",

      // History Modal
      historyModalTitle: "Search History",
      historyModalDesc: "Archive of past searches and downloadable packages",
      clearHistoryBtn: "Clear All History",
      historyEmptyText: "No previous searches found. Completed searches will appear here.",
      historyDownloadBtn: "📥 Download File",
      historyViewBtn: "👁 View File",
      historyDeleteBtn: "Delete",

      // Settings Modal
      settingsModalTitle: "Researcher & Academic Source Settings",
      settingsEmailLabel: "Academic Email (Polite Pool for Crossref & Unpaywall)",
      settingsElsevierLabel: "Scopus / Elsevier API Key (Optional)",
      settingsElsevierPlaceholder: "Enter key to activate Scopus, or leave blank",
      settingsElsevierNote: "💡 For direct Scopus / ScienceDirect access, enter your key above. If left blank, the system automatically queries 9 other open science databases.",
      settingsStatusHeader: "Academic Repositories & Database Status (10 Repositories):",
      statusConnected: "🟢 Connected",
      statusActive: "🟢 Active",
      statusInactive: "⚪ Inactive",
      saveSettingsBtn: "💾 Save Settings",
      savingBtn: "Saving...",

      // Search Scope & Document Type Filters
      searchScopeLabel: "Search Scope",
      scopeAll: "Comprehensive (Papers & Books)",
      scopePapers: "Academic Papers & Articles Only",
      scopeBooks: "Books & Monographs Only",
      docTypeLabel: "Document Type Filter",
      docTypeAll: "All Document Types",
      docTypeReview: "Review Articles (Literature & Systematic)",
      docTypeMetaAnalysis: "Meta-Analyses Only",
      docTypeResearch: "Original Research Articles",
      docTypeBook: "Books & Book Chapters",
      docTypeConference: "Conference Proceedings",
      filterReviews: "Reviews",
      filterBooks: "Books",
      filterResearch: "Research Articles",
      badgeReview: "Review Article",
      badgeMetaAnalysis: "Meta-Analysis",
      badgeBook: "Book / Chapter",
      badgeConference: "Conference Paper",
      badgeResearch: "Research Article",

      // Footer
      footerTagline: "Knowledge Ocean v1.0 • Canonical Architecture • Multi-Source Scholarly Retrieval",
      footerDownloadLocal: "💻 Download Standalone Local Edition (ZIP)",

      // Alerts & Messages
      alertEnterQuery: "Please enter a search keyword or topic",
      alertElsevierGuest: "Scopus (Elsevier) is unavailable for guests and requires VIP access or local edition.",
      alertSendingRequest: "Sending request to academic search engines...",
      alertSearchStarted: "Multi-threaded academic discovery and indexing started...",
      alertServerOffline: "Unable to connect to server — please verify backend is running",
      alertSearchCancelled: "Search cancelled",
      alertSearchFailed: "Search operation failed",
      alertCopySuccess: "Copied to clipboard successfully"
    },
    ar: {
      appName: "Knowledge Ocean",
      appVersion: "v1.0",
      subtitle: "استرجاع وتوثيق أكاديمي فائق الدقة",
      developerCredit: "Developed by ABDULSALAM S. HASAN",
      vipUnlimitedBadge: "✨ VIP Access Active (Unlimited Searches)",
      quotaBadgeText: "رصيد الضيوف: 50 بحثاً (يتجدد تلقائياً 12:00 ص بتوقيت بغداد)",
      quotaExhaustedAlert: "نفد رصيد البحث التجريبي اليومي (50 بحث قياسي أو 25 مع ملخصات). يتجدد الرصيد تلقائياً عند الساعة 12:00 ص بتوقيت بغداد (UTC+3)، أو يرجى إدخال مفتاح الوصول (VIP).",

      offlineBadge: "النسخة المحلية المستقلة (Offline Ready)",
      downloadLocalZip: "تحميل النسخة المحلية (ZIP)",
      downloadLocalZipTitle: "تحميل النسخة المحلية للتشغيل المستقل بدون قيود على جهازك",
      settingsBtn: "الإعدادات والمصادر",
      settingsTitle: "إعدادات الباحث ومصادر البحث الأكاديمي",
      themeDarkTooltip: "التبديل إلى الوضع الليلي",
      themeLightTooltip: "التبديل إلى الوضع النهاري",
      langSwitchTooltip: "Switch to English (التبديل إلى الإنجليزية)",
      langTargetLabel: "EN",

      // Nav Tabs
      tabExplorer: "المستودع الأكاديمي الشامل",
      tabDoiHub: "منظومة توثيق ومعرّفات DOI",
      instantLookupBadge: "استعلام وتوثيق فوري",

      // DOI Hub Header
      doiHubTitle: "منظومة التوثيق الأكاديمي ومعرّفات DOI",
      doiHubSubtitle: "بوابة فحص واسترجاع بيانات الأبحاث الأكاديمية عبر المعرّف الرقمي المعتمد عالمياً (DOI)، أو مطابقة عناوين الأبحاث لاستخراج المعرّفات والبيانات الوصفية الرسمية بدقة متناهية مع روابط مباشرة وتوثيق APA / BibTeX فوري.",
      returnToExplorer: "العودة للمستودع الأكاديمي الشامل",
      doiSubtabDirect: "فحص واستعلام معرّف DOI",
      doiSubtabTitle: "استخراج المعرّف من العنوان",

      // DOI Direct Tab
      doiInputLabel: "أدخل معرّف DOI المباشر أو رابطه الكامل",
      doiInputPlaceholder: "مثال: 10.1007/s40278-024-60584-4 أو https://doi.org/10.1186/s13256-025-05459-w",
      doiLookupBtn: "فحص واسترجاع المعرف 🔍",
      doiLookupLoading: "جاري الاستعلام...",
      doiExamplesLabel: "أمثلة معرّفات للتجربة السريعة:",
      peerReviewed: "بحث محكّم",
      preprint: "مسودة (Preprint)",
      openAccess: "وصول مفتوح",
      citationsCount: "استشهاد",
      sourcesLabel: "المصادر:",
      publisherSubNotice: "(البحث خاضع لاشتراك الناشر — الرابط الرسمي متاح أعلاه)",
      downloadFullOa: "📥 تحميل / قراءة البحث الكامل (Open Access)",
      scihubConfirmedBtn: "مستودع بديل (Sci-Hub)",
      scihubSearchBtn: "البحث في Sci-Hub",
      scihubSearchTitle: "البحث والتحقق في مستودع Sci-Hub",
      rgDownloadBtn: "📥 متاح للتنزيل (ResearchGate)",
      rgSearchBtn: "البحث في ResearchGate",
      rgSearchTitle: "البحث والتحقق من توفر البحث وتنزيله عبر منصة ResearchGate",
      copyApaBtn: "نسخ APA 7th",
      copyBibtexBtn: "نسخ BibTeX",
      copyRisBtn: "نسخ RIS",
      copiedApaAlert: "تم نسخ توثيق APA بنجاح",
      copiedBibtexAlert: "تم نسخ كود BibTeX بنجاح",
      copiedRisAlert: "تم نسخ كود RIS بنجاح",

      // DOI Title Tab
      titleInputLabel: "أدخل العنوان الكامل للبحث العلمي لاستخراج المعرف وتوثيقه",
      titleInputPlaceholder: "مثال: Determination of ibuprofen and naproxen in tablets...",
      titleFindBtn: "استخراج المعرف 🔍",
      titleFindLoading: "جاري البحث في القواعد الأكاديمية...",
      titleMatchHeader: "أبحاث مطابقة ومؤكدة تم العثور عليها:",
      detailedCheckBtn: "🔍 فحص تفصيلي",
      searchRgTitle: "البحث في منصة ResearchGate",
      searchScihubTitle: "البحث في مستودع Sci-Hub",

      // Explorer Top Banners
      localBannerText: "⚡ أنت تعمل الآن في بيئة التشغيل المحلي المستقلة — يتم حفظ ملفات PDF المجمعة مباشرة على جهازك وتعمل الواجهة بدون الحاجة لإنترنت خارجي.",
      cloudBannerTitle: "تشغيل محيط المعرفة محلياً على حاسوبك الشخصي",
      cloudBannerBadge: "نسخة كاملة مستقلة",
      cloudBannerDesc: "بإمكانك تنزيل الحزمة المحمولة وتشغيل السيرفر على جهازك بنقرة زر واحدة عبر سكريبت run_local.bat للبحث السريع، حفظ الملفات مباشرة على حاسوبك، وتجاوز أي قيود.",
      cloudBannerBtn: "تحميل حزمة التشغيل المحلي (ZIP) ↓",

      // Search Form
      searchSettingsTitle: "إعدادات واستعلام البحث الشامل",
      localFullBadge: "نسخة محلية مفتوحة بالكامل (استخراج شامل بلا قيود وبلا رمز)",
      cloudQuotaBadge: "الاستخدام السحابي (50 بحثاً مع فهرس شامل مفصل)",
      operationModeLabel: "وضع التشغيل الأكاديمي",
      localAccessText: "وصول محلي كامل ومفتوح (بدون رمز)",
      historyBtn: "سجل الأبحاث ◫",
      historyBtnLoading: "جاري...",
      accessKeyLabel: "مفتاح الوصول (VIP)",
      accessKeyPlaceholder: "أدخل مفتاح الوصول لبحث غير محدود...",
      searchModeLabel: "نمط البحث",
      modeKeyword: "كلمات متفرقة (Keywords + Boolean: AND, OR, NOT)",
      modeAuthor: "اسم الباحث (Author Mode)",
      modeExact: "تطابق تام (Exact Match)",
      modeDoi: "🎯 معرف DOI مباشر (انتقال فوري للمنظومة التوثيقية ↗)",
      modeTitleDoi: "📑 البحث باسم البحث لإيجاد الـ DOI (انتقال فوري للمنظومة التوثيقية ↗)",
      queryLabel: "الاستعلام البحثي (Search Query / DOI / Keywords)",
      clearQueryBtn: "مسح الاستعلام ✕",
      queryPlaceholder: "اكتب موضوع البحث، كلمات مفتاحية، عنوان دراسة، أو اسم باحث...",
      exampleQueriesLabel: "أمثلة استعلامات للتجربة السريعة:",

      // Advanced Filters
      strictTitleLabel: "فلتر العنوان الإلزامي (Title Must Filter)",
      strictTitlePrecisionBadge: "دقة استهداف 99%",
      strictTitleDesc: "تحديد نطاق مطابقة الكلمات: هل يُشترط وجودها في عنوان البحث نفسه، أم يُكتفى بوجودها في العنوان أو الملخص.",
      strictTitleOnBadge: "مُفعّل (ON) - حصر إلزامي في العنوان",
      strictTitleOnText: "يستبعد أي دراسة لا تتضمن كلمات البحث صراحةً في عنوانها (Title)، مما يضمن أعلى دقة وتطابقاً بنسبة 99%. يواصل المحرك المسح التكراري لقواعد البيانات حتى استيفاء العدد المطلوب كاملاً أو نفاد النتائج المتاحة. (موصى به عند البحث عن موضوع دقيق ومحدد).",
      strictTitleOffBadge: "غير مُفعّل (OFF) - بحث شامل وتغطية قصوى (الافتراضي)",
      strictTitleOffText: "يبحث عن الكلمات في العناوين والملخصات معاً لضمان عدم تفويت أي دراسة قيّمة ذات صلة قد تذكر الموضوع داخل ملخصها. يتم ترتيب النتائج بذكاء بحيث تتصدر الأبحاث التي تطابق كلماتها في العنوان أولاً، تليها الأكثر صلة موضوعياً. (موصى به للاستكشاف الأكاديمي الشامل وتغطية كافة جوانب الموضوع).",
      timeRangeLabel: "النطاق الزمني (الفترة)",
      yearFromPlaceholder: "من (مثال 2020)",
      yearToPlaceholder: "إلى (مثال 2026)",
      yearPresetRange: "2020 - 2026",
      yearPresetNow: "السنة الحالية فقط",
      yearPresetAll: "جميع السنوات",
      maxResultsLabel: "الحد الأقصى للنتائج",
      limit5: "5 أبحاث",
      limit10: "10 أبحاث",
      limit25: "25 بحثاً",
      limit50: "50 بحثاً",
      limit100: "100 نتيجة",
      limit250: "250 نتيجة",
      limitAll: "شامل لايجاد كل ما هو موجود",
      dbSourcesLabel: "قواعد البيانات والمصادر",
      sourceAll: "شامل لايجاد كل ما هو موجود (12 محركاً)",
      sourcePubmed: "PubMed (طبية وحيوية)",
      sourceElsevierLocal: "Scopus (Elsevier)",
      sourceElsevierCloud: "Scopus (Elsevier) [يتطلب مفتاح VIP]",
      sourceEuropepmc: "Europe PMC",
      sourceOpenalex: "OpenAlex",
      sourceCrossref: "CrossRef",
      sourceSemantic: "Semantic Scholar",
      sourceDoaj: "DOAJ (وصول حر Open Access)",
      sourceCore: "CORE (وصول حر)",
      sourceZenodo: "Zenodo (CERN / Open Access)",
      sourceBooks: "مكتبات الكتب (Google Books, Open Library)",
      preprintsLabel: "المسودات (Preprints)",
      includePreprintsText: "تضمين مسودات ما قبل النشر (arXiv, bioRxiv, OpenAlex...)",
      affiliationLabel: "الانتماء المؤسسي (اختياري - لمطابقة الجامعة أو المركز)",
      affiliationPlaceholder: "مثال: University of Mosul, Harvard University...",
      fulltextScrapingLabel: "تنزيل الأبحاث الكاملة (Full-Text Paper Scraping)",
      fulltextScrapingBadge: "خيار اختياري متقدم",
      fulltextScrapingDesc: "تضمين ملخصات الأبحاث الشاملة في النتائج وملفات التقارير الأكاديمية",
      fulltextWarningTitle: "تنبيه هام بشأن استهلاك الوقت:",
      fulltextWarningText: "تنزيل الأبحاث الكاملة يتطلب وقتاً إضافياً (قد يستغرق دقائق بحسب عدد الأبحاث وسرعة خوادم الناشرين).",
      fulltextQualityBadge: "ضمان الجودة الأكاديمية: تم إلغاء تنزيل واجهات HTML تماماً؛ لن يتم حفظ أي ملف إلا بعد التحقق من كونه ملف PDF أكاديمياً حقيقياً (%PDF).",
      fulltextDisabledNote: "معطّل افتراضياً لسرعة البحث وتوليد الملخصات والفهارس في ثوانٍ معدودة.",
      startSearchBtn: "بدء البحث الأكاديمي 🔍",
      searchingBtn: "جاري البحث...",
      cancelSearchBtn: "إلغاء البحث",

      // Results Section
      retrievedHeader: "الأبحاث والدراسات المسترجعة",
      papersRetrievedCount: "بحثاً تم استرجاعها",
      filterAll: "كافة الأبحاث",
      filterPeer: "أبحاث محكّمة",
      filterPreprints: "مسودات",
      filterOa: "وصول مفتوح",
      filterResultsPlaceholder: "تصفية النتائج الحالية (بالعنوان، المجلة، الباحث، الـ DOI)...",
      downloadResultsZip: "تحميل النتائج (ZIP)",
      viewResultsFile: "عرض الملف",
      directLinkDownload: "↗ رابط مباشر / تحميل",
      checkingAvailability: "جاري فحص التوفر...",
      freeOaDownload: "📥 تحميل مجاني (Open Access)",
      publisherSubscription: "🔒 خاضع لاشتراك الناشر",
      checkFreeAccessBtn: "🔍 فحص التوفر المجاني",
      badgeAvailable: "متوفر",
      badgeDownload: "تنزيل",
      copyDoiLinkBtn: "📋 نسخ رابط الـ DOI",
      copyDoiLinkDone: "✓ تم نسخ الرابط",
      readAbstractBtn: "قراءة الملخص",
      hideAbstractBtn: "إخفاء الملخص",
      noAbstractText: "لا يتوفر ملخص نصي لهذه الدراسة في البيانات الوصفية المفتوحة.",

      // Modals
      abstractModalTitle: "ملخص البحث الأكاديمي",
      copyAbstractBtn: "📋 نسخ الملخص",
      copyAbstractDone: "✓ تم النسخ",
      modalCloseBtn: "إغلاق",
      downloadCompleteTitle: "اكتمل استخراج وفهرسة الأبحاث بنجاح",
      downloadCompleteDesc: "تم إعداد الملف الشامل وتوليد الفهارس الأكاديمية والتوثيقات بنجاح.",
      downloadPackageBtn: "📥 تنزيل الحزمة الكاملة",
      viewFileBtn: "👁 عرض ملف النتائج",

      // History Modal
      historyModalTitle: "سجل عمليات البحث السابقة",
      historyModalDesc: "سجل المحفوظات السابقة لعمليات البحث والملفات المحملة",
      clearHistoryBtn: "مسح السجل بالكامل",
      historyEmptyText: "لا توجد عمليات بحث سابقة محفوظة. ستظهر نتائج أبحاثك المكتملة هنا.",
      historyDownloadBtn: "📥 تحميل الملف",
      historyViewBtn: "👁 عرض الملف",
      historyDeleteBtn: "حذف",

      // Settings Modal
      settingsModalTitle: "إعدادات الباحث ومصادر البحث الأكاديمي",
      settingsEmailLabel: "البريد الأكاديمي (Polite Pool لـ Crossref و Unpaywall)",
      settingsElsevierLabel: "مفتاح Scopus / Elsevier API (اختياري)",
      settingsElsevierPlaceholder: "أدخل المفتاح لتفعيل Scopus، أو اتركه فارغاً",
      settingsElsevierNote: "💡 للوصول المباشر لقاعدة Scopus / ScienceDirect يرجى إدخال المفتاح أعلاه. في حال تركه فارغاً، يعتمد النظام تلقائياً على المستوعبات الأكاديمية التسعة الأخرى بكفاءة تامة.",
      settingsStatusHeader: "حالة المستوعبات وقواعد البيانات الأكاديمية (10 مستوعبات):",
      statusConnected: "🟢 متصل",
      statusActive: "🟢 نشط",
      statusInactive: "⚪ غير مفعل",
      saveSettingsBtn: "💾 حفظ التغييرات",
      savingBtn: "جاري الحفظ...",

      // Search Scope & Document Type Filters
      searchScopeLabel: "نطاق البحث الأكاديمي",
      scopeAll: "بحث شامل (أبحاث ومقالات علمية + كتب ومراجع)",
      scopePapers: "أبحاث ومقالات علمية فقط",
      scopeBooks: "كتب ومراجع وفصول كتب فقط",
      docTypeLabel: "تصفية نوع الوثيقة",
      docTypeAll: "كافة أنواع الوثائق",
      docTypeReview: "مراجعات علمية شاملة (Review Articles)",
      docTypeMetaAnalysis: "تحليلات تجميعية (Meta-Analyses)",
      docTypeResearch: "أبحاث ومقالات أصيلة (Original Research)",
      docTypeBook: "كتب وفصول كتب (Books & Chapters)",
      docTypeConference: "أوراق مؤتمرات (Conference Papers)",
      filterReviews: "مراجعات علمية",
      filterBooks: "كتب ومراجع",
      filterResearch: "أبحاث أصيلة",
      badgeReview: "مراجعة علمية",
      badgeMetaAnalysis: "تحليل تجميعي",
      badgeBook: "كتاب / فصل",
      badgeConference: "ورقة مؤتمر",
      badgeResearch: "بحث أصيل",

      // Footer
      footerTagline: "Knowledge Ocean v1.0 • Canonical Architecture • Multi-Source Scholarly Retrieval",
      footerDownloadLocal: "💻 تنزيل حزمة التشغيل المحلي المستقلة (ZIP)",

      // Alerts & Messages
      alertEnterQuery: "يرجى إدخال كلمة أو مصطلح البحث",
      alertElsevierGuest: "قاعدة Scopus (Elsevier) غير متاحة للضيوف وتتطلب إدخال مفتاح الوصول (VIP) أو استخدام النسخة المحلية.",
      alertSendingRequest: "جاري إرسال الطلب لمحركات البحث الأكاديمية...",
      alertSearchStarted: "بدأت عملية المسح والتجميع والتدقيق المتوازي...",
      alertServerOffline: "تعذر الاتصال بالخادم — تأكد من تشغيل السيرفر",
      alertSearchCancelled: "تم إلغاء عملية البحث",
      alertSearchFailed: "فشلت عملية البحث",
      alertCopySuccess: "تم النسخ بنجاح"
    }
  };

  // Task Message Localizer (Ensures English UI never displays raw Arabic status text)
  function localizeTaskMessage(msg, targetLang) {
    if (!msg || typeof msg !== 'string') {
      return targetLang === 'ar' ? 'جاري المعالجة...' : 'Processing...';
    }
    if (targetLang === 'ar') return msg;

    let m = msg.trim();

    // Universal replacements of common Arabic status words
    m = m.replace(/تم التنزيل/g, 'Downloaded')
         .replace(/تعذّر/g, 'Unavailable')
         .replace(/تنزيل الأبحاث الكاملة/g, 'Downloading full-text papers')
         .replace(/نجاح/g, 'Success')
         .replace(/تخطي/g, 'Skipped')
         .replace(/فشل/g, 'Failed');

    if (m.includes('بدء مسح وتدقيق الأبحاث')) {
      return 'Scanning and searching academic engines...';
    }
    if (m.includes('في الطابور')) {
      const p = m.match(/\d+/g);
      return p && p.length >= 2 ? ('In queue (Position: ' + p[0] + ' of ' + p[1] + ')...') : 'In queue...';
    }
    if (m.includes('تم فرز') && (m.includes('توليد ملفات PDF') || m.includes('PDF report'))) {
      const n = m.match(/\d+/);
      return n ? ('Sorted ' + n[0] + ' papers — generating PDF files...') : 'Papers sorted — generating PDF files...';
    }
    if (m.includes('جاري إعداد وتنسيق ملف الأبحاث')) {
      const n = m.match(/\d+/);
      return n ? ('Formatting and compiling PDF research report (' + n[0] + ' papers)...') : 'Formatting and compiling PDF research report...';
    }
    if (m.includes('تم جمع وتدقيق')) {
      const p = m.match(/\d+/g);
      return p && p.length >= 2 ? ('Collected and verified ' + p[0] + ' of ' + p[1] + ' papers...') : 'Collecting and verifying papers...';
    }
    if (m.includes('جاري البحث الشامل')) {
      const p = m.match(/\d+/g);
      return p && p.length >= 2 ? ('Comprehensive search: Collected and verified ' + p[0] + ' papers so far (Round ' + p[1] + ')...') : 'Comprehensive search in progress...';
    }
    if (m.includes('اكتمل الاستخراج بنجاح') || m.includes('Extraction completed successfully')) {
      return m.replace('اكتمل الاستخراج بنجاح!', 'Extraction completed successfully!')
              .replace('تم إعداد ملف الأبحاث', 'Research package generated')
              .replace('تم العثور على', 'Found')
              .replace('بحث محكّم', 'peer-reviewed')
              .replace('مسودة', 'preprints');
    }
    if (m.includes('تم إيقاف البحث بنجاح') || m.includes('Search stopped successfully')) {
      return m.replace('تم إيقاف البحث بنجاح!', 'Search stopped successfully!')
              .replace('تم إعداد ملف الأبحاث بما تم جمعه', 'Document generated with collected papers')
              .replace('بحث محكّم', 'peer-reviewed')
              .replace('مسودة', 'preprints');
    }
    if (m.includes('تم إيقاف البحث — جاري الآن')) {
      return 'Search stopped — generating document with collected papers...';
    }
    if (m.includes('تم إيقاف البحث بناءً على طلبك')) {
      return m.replace('تم إيقاف البحث بناءً على طلبك', 'Search stopped upon your request')
              .replace('وحفظ', 'and saved')
              .replace('بنجاح!', 'successfully!')
              .replace('بحث محكّم', 'peer-reviewed')
              .replace('مسودة', 'preprints');
    }
    if (m.includes('ضغط') && m.includes('ZIP')) {
      const n = m.match(/\d+/);
      return n ? ('Compressing ' + n[0] + ' files into ZIP archive...') : 'Compressing files into ZIP archive...';
    }
    if (m.includes('تم إلغاء البحث')) {
      return 'Search cancelled upon your request.';
    }
    if (m.includes('البحث في')) {
      return m.replace(/البحث في/g, 'Searching');
    }
    if (m.includes('تنبيه: تعذّر إكمال تنزيل الأبحاث الكاملة') || m.includes('Notice: Could not complete full-text download')) {
      return 'Notice: Could not complete full-text download.';
    }
    if (m.includes('جاري إرسال الطلب')) {
      return 'Sending request to academic search engines...';
    }
    if (m.includes('إعادة محاولة الاتصال')) {
      return 'Retrying server connection...';
    }
    if (m.includes('جاري المعالجة')) {
      return 'Processing...';
    }

    return m;
  }

  function getOrCreateGuestToken() {
    try {
      let token = localStorage.getItem("ko_guest_token");
      if (!token || typeof token !== "string" || token.length < 10) {
        const randArr = new Uint8Array(16);
        if (window.crypto && window.crypto.getRandomValues) {
          window.crypto.getRandomValues(randArr);
          token = "gt_" + Date.now().toString(36) + "_" + Array.from(randArr, b => b.toString(16).padStart(2, '0')).join('');
        } else {
          token = "gt_" + Date.now().toString(36) + "_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        }
        localStorage.setItem("ko_guest_token", token);
      }
      return token;
    } catch (_) {
      return "gt_guest_token";
    }
  }

  function App() {
    // Language State: 'en' (Default) or 'ar'
    const [lang, setLang] = useState(() => {
      try {
        const saved = localStorage.getItem("knowledge_ocean_lang");
        if (saved === "ar" || saved === "en") return saved;
      } catch (e) {}
      return "en";
    });

    const t = I18N[lang] || I18N.en;

    // Guest Quota Management (50 standard searches or 25 with summaries for guests; 250 daily for secondary key)
    const [password, setPassword] = useState(() => {
      try {
        return "";
      } catch (e) {
        return "";
      }
    });
    const [showAccessCode, setShowAccessCode] = useState(false);
    const [showLoginModal, setShowLoginModal] = useState(false);
    const [loginInputCode, setLoginInputCode] = useState("");
    const [loginShowPassword, setLoginShowPassword] = useState(false);
    const [loginLoading, setLoginLoading] = useState(false);
    const [loginError, setLoginError] = useState("");
    const [loginSuccessMsg, setLoginSuccessMsg] = useState("");
    const [loginAttemptsLeft, setLoginAttemptsLeft] = useState(null);
    const [isIpBanned, setIsIpBanned] = useState(false);
    const [banRemainingSec, setBanRemainingSec] = useState(0);

    const [quota, setQuota] = useState({ limit: 50, remaining: 50, remainingSummary: 25, isVip: false });
    const [activeTaskInfo, setActiveTaskInfo] = useState(null);

    const fetchQuota = async (pwd) => {
      try {
        const p = pwd !== undefined ? pwd : password;
        const res = await fetch(`/api/guest-quota?guest_token=${encodeURIComponent(getOrCreateGuestToken())}`, { cache: "no-store" });
        if (res.ok) {
          const d = await res.json();
          if (d.banned) {
            setIsIpBanned(true);
            setBanRemainingSec(d.remaining_seconds || 86400);
          } else {
            setIsIpBanned(false);
          }
          const defLimit = d.is_other ? 250 : 50;
          const lim = d.quota_limit || defLimit;
          setQuota({
            limit: lim,
            remaining: (d.remaining !== undefined) ? d.remaining : lim,
            remainingSummary: (d.remaining_summary !== undefined) ? d.remaining_summary : Math.floor(lim / 2),
            isVip: d.is_vip || false,
            isOther: d.is_other || false,
            autoRenew: d.auto_renew || false
          });

          if (d.active_task) {
            setActiveTaskInfo(d.active_task);
          }
        }
      } catch (e) {}
    };

    const handleLogin = async (codeToSubmit) => {
      const code = (codeToSubmit !== undefined ? codeToSubmit : loginInputCode).trim();
      if (!code) {
        setLoginError(lang === "ar" ? "يرجى إدخال رمز المرور  " : "Please enter access code ");
        return;
      }
      setLoginLoading(true);
      setLoginError("");
      setLoginSuccessMsg("");
      try {
        const res = await fetch("/api/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password: code })
        });
        const data = await res.json();
        if (res.ok && data.status === "success") {
          setPassword(code);
          try {
            localStorage.removeItem("ko_access_code");
          } catch (e) {}
          setLoginSuccessMsg(data.message || (lang === "ar" ? "تم تفعيل الرمز بنجاح!" : "Access code activated successfully!"));
          setLoginError("");
          setLoginAttemptsLeft(null);
          setIsIpBanned(false);
          await fetchQuota(code);
          setTimeout(() => {
            setShowLoginModal(false);
            setLoginSuccessMsg("");
          }, 1500);
        } else {
          if (data.banned || res.status === 403) {
            setIsIpBanned(true);
            setBanRemainingSec(data.remaining_seconds || 86400);
            setLoginError(data.error || (lang === "ar" ? "تم حظر هذا الـ IP لمدة 24 ساعة بسبب تكرار المحاولات الخاطئة." : "IP address banned for 24 hours."));
          } else {
            setLoginAttemptsLeft(data.attempts_left !== undefined ? data.attempts_left : null);
            setLoginError(data.error || (lang === "ar" ? "الرمز غير صحيح! تحقق من الرمز وأعد المحاولة." : "Invalid code. Please try again."));
          }
        }
      } catch (err) {
        setLoginError(lang === "ar" ? "تعذر الاتصال بالخادم، يرجى المحاولة لاحقاً." : "Network error, please try again.");
      } finally {
        setLoginLoading(false);
      }
    };

    const handleLogout = () => {
      setPassword("");
      try {
        localStorage.removeItem("ko_access_code");
      } catch (e) {}
      setLoginInputCode("");
      setLoginError("");
      setLoginAttemptsLeft(null);
      setLoginSuccessMsg(lang === "ar" ? "تم تسجيل الخروج بنجاح والعودة للوضع المجاني." : "Logged out successfully. Switched to guest tier.");
      fetch("/api/logout", { method: "POST" }).finally(() => fetchQuota(""));
      setTimeout(() => {
        setShowLoginModal(false);
        setLoginSuccessMsg("");
      }, 1200);
    };

    useEffect(() => {
      fetchQuota(password);
      const onFocus = () => fetchQuota(password);
      window.addEventListener("focus", onFocus);
      const onVisibility = () => {
        if (document.visibilityState === "visible") fetchQuota(password);
      };
      document.addEventListener("visibilitychange", onVisibility);
      const timer = setInterval(() => fetchQuota(password), 60000);
      return () => {
        window.removeEventListener("focus", onFocus);
        document.removeEventListener("visibilitychange", onVisibility);
        clearInterval(timer);
      };
    }, [password]);


    useEffect(() => {
      try {
        localStorage.setItem("knowledge_ocean_lang", lang);
      } catch (e) {}
      document.documentElement.lang = lang;
      document.documentElement.dir = (lang === "ar" ? "rtl" : "ltr");
      document.title = "Knowledge Ocean";
    }, [lang]);

    const [query, setQuery] = useState("");
    const [mode, setMode] = useState("keyword");
    const [dbSource, setDbSource] = useState("all");
    const [limit, setLimit] = useState("50");
    const [affiliation, setAffiliation] = useState("");
    const [requireTitle, setRequireTitle] = useState(false);
    const [yearFrom, setYearFrom] = useState("");
    const [yearTo, setYearTo] = useState("");
    const [includePreprint, setIncludePreprint] = useState(false);
    const [includeAbstracts, setIncludeAbstracts] = useState(false);
    const [searchScope, setSearchScope] = useState("all"); // 'all', 'papers', 'books'
    const [docTypeFilter, setDocTypeFilter] = useState("all"); // 'all', 'review', 'meta_analysis', 'research', 'book', 'conference' 

    const [isSearching, setIsSearching] = useState(false);
    const [taskId, setTaskId] = useState(null);
    const [progress, setProgress] = useState(0);
    const [statusMsg, setStatusMsg] = useState(() => (lang === "ar" ? "جاري التهيئة..." : "Initializing..."));
    const [counts, setCounts] = useState(null);

    const [downloadUrl, setDownloadUrl] = useState("#");
    const [fileType, setFileType] = useState("zip"); // 'zip' or 'pdf'
    const [filename, setFilename] = useState("");
    const [abstractModalPaper, setAbstractModalPaper] = useState(null);
    const [showAbstractModal, setShowAbstractModal] = useState(false);
    const [copiedModalAbstract, setCopiedModalAbstract] = useState(false);
    const [mdUrl, setMdUrl] = useState("#");
    const [savePath, setSavePath] = useState("");
    const [copiedPath, setCopiedPath] = useState(false);
    const [showDownloadPanel, setShowDownloadPanel] = useState(false);
    const [showModal, setShowModal] = useState(false);
    const [doneTitle, setDoneTitle] = useState(() => (lang === "ar" ? "اكتمل البحث" : "Search Completed"));
    const [alertInfo, setAlertInfo] = useState({ text: null, type: "error" });

    // Live Paper Results State
    const [resultsPapers, setResultsPapers] = useState([]);
    const [paperFilter, setPaperFilter] = useState("all"); // 'all', 'peer', 'preprints', 'oa'
    const [resultsQuery, setResultsQuery] = useState("");
    const [expandedAbstracts, setExpandedAbstracts] = useState({});
    const [copiedCiteId, setCopiedCiteId] = useState(null);
    const [cardAccessMap, setCardAccessMap] = useState({});
    const [cardCheckingMap, setCardCheckingMap] = useState({});

    // Dedicated DOI Hub States
    const [activeNavTab, setActiveNavTab] = useState("explorer"); // 'explorer' or 'doi_hub'
    const [doiTab, setDoiTab] = useState("doi"); // 'doi' or 'title'
    const [doiInput, setDoiInput] = useState("");
    const [doiLoading, setDoiLoading] = useState(false);
    const [doiResult, setDoiResult] = useState(null);
    const [copiedDoiLink, setCopiedDoiLink] = useState(false);
    const [copiedDoiRaw, setCopiedDoiRaw] = useState(false);
    const [copiedDoiApa, setCopiedDoiApa] = useState(false);
    const [titleInput, setTitleInput] = useState("");
    const [titleLoading, setTitleLoading] = useState(false);
    const [titleResults, setTitleResults] = useState([]);
    const [copiedTitleDoiLink, setCopiedTitleDoiLink] = useState(null);
    const [copiedTitleApa, setCopiedTitleApa] = useState(null);
    const [copiedDoiUrlId, setCopiedDoiUrlId] = useState(null);
    const [doiAbstractExpanded, setDoiAbstractExpanded] = useState(false);

    // User Settings & Onboarding States
    const [showFirstRunModal, setShowFirstRunModal] = useState(false);
    const [showSettingsModal, setShowSettingsModal] = useState(false);
    const [settingsEmail, setSettingsEmail] = useState("contact@example.com");
    const [settingsElsevierKey, setSettingsElsevierKey] = useState("");
    const [settingsSaving, setSettingsSaving] = useState(false);
    const [settingsStatusMsg, setSettingsStatusMsg] = useState(null);
    const [providerStatuses, setProviderStatuses] = useState(null);

    const [historyList, setHistoryList] = useState([]);
    const [isDark, setIsDark] = useState(() => {
      try {
        const saved = localStorage.getItem("ko_dark_theme");
        return saved !== null ? saved === "true" : true;
      } catch (e) {
        return true;
      }
    });
    const [loadingHistory, setLoadingHistory] = useState(false);

    const pollingRef = useRef(null);
    const queryInputRef = useRef(null);
    const resultsSectionRef = useRef(null);

    const isFileProtocol = typeof window !== "undefined" && window.location.protocol === "file:";
    const isHfSpace = typeof window !== "undefined" && (
      window.__IS_HF_SPACE__ === true ||
      window.location.hostname.includes("hf.space") ||
      window.location.hostname.includes("huggingface.co")
    );
    const isLocal = typeof window !== "undefined" && !isHfSpace && (
      window.__IS_LOCAL_INSTANCE__ === true ||
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1" ||
      window.location.hostname.endsWith(".local") ||
      isFileProtocol
    );

    // Theme effect
    useEffect(() => {
      if (isDark) {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }
      try {
        localStorage.setItem("ko_dark_theme", isDark ? "true" : "false");
      } catch (e) {}
    }, [isDark]);

    // Keyboard shortcuts
    useEffect(() => {
      const handleKeyDown = (e) => {
        if (e.key === "Escape") {
          if (showAbstractModal) setShowAbstractModal(false);
          if (showSettingsModal) setShowSettingsModal(false);
          if (showFirstRunModal) setShowFirstRunModal(false);
          if (showModal) setShowModal(false);
          if (alertInfo.text) setAlertInfo({ text: null, type: "error" });
        }
      };
      window.addEventListener("keydown", handleKeyDown);
      return () => window.removeEventListener("keydown", handleKeyDown);
    }, [showAbstractModal, showSettingsModal, showFirstRunModal, showModal, alertInfo]);

    const loadSettings = () => {
      fetch("/api/settings")
        .then(r => r.json())
        .then(data => {
          if (data) {
            if (data.unpaywall_email) setSettingsEmail(data.unpaywall_email);
            if (data.elsevier_api_key !== undefined) setSettingsElsevierKey(data.elsevier_api_key || "");
            if (data.providers) setProviderStatuses(data.providers);
          }
        })
        .catch(() => {});
    };

    const saveSettings = async (emailVal, keyVal, isFirstRun = false) => {
      setSettingsSaving(true);
      setSettingsStatusMsg(null);
      try {
        const res = await fetch("/api/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            unpaywall_email: emailVal,
            elsevier_api_key: keyVal
          })
        });
        const data = await res.json();
        if (data.status === "success") {
          setSettingsStatusMsg({ type: "success", text: lang === "ar" ? "✓ تم حفظ الإعدادات بنجاح!" : "✓ Settings saved successfully!" });
          if (isFirstRun) {
            try { localStorage.setItem("ko_first_run_completed", "true"); } catch(e){}
            setTimeout(() => {
              setShowFirstRunModal(false);
              setSettingsStatusMsg(null);
            }, 800);
          } else {
            setTimeout(() => setSettingsStatusMsg(null), 3000);
          }
          loadSettings();
        } else {
          setSettingsStatusMsg({ type: "error", text: data.detail || data.message || (lang === "ar" ? "الإعدادات تُضبط من خادم التطبيق أو Secrets" : "Configure settings in server environment / secrets") });
          if (isFirstRun && isLocal) {
            try { localStorage.setItem("ko_first_run_completed", "true"); } catch (_) {}
            setShowFirstRunModal(false);
          }
        }
      } catch (err) {
        setSettingsStatusMsg({ type: "error", text: lang === "ar" ? "تعذر الاتصال بالخادم لحفظ الإعدادات" : "Unable to connect to server to save settings" });
      } finally {
        setSettingsSaving(false);
      }
    };

    // Load settings, search history, and check first run on mount
    useEffect(() => {
      loadSettings();
      loadHistory(true);
      try {
        const firstRunDone = localStorage.getItem("ko_first_run_completed");
        if (!firstRunDone && isLocal) {
          setShowFirstRunModal(true);
        }
      } catch(e) {}
    }, [isLocal]);

    const showAlert = (text, type = "error", duration = 5000) => {
      setAlertInfo({ text, type });
      if (text && duration > 0) {
        setTimeout(() => setAlertInfo({ text: null, type: "error" }), duration);
      }
    };

    const copyToClipboard = (text, successCallback) => {
      if (!text) return;
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
          if (successCallback) successCallback();
        }).catch(() => {
          fallbackCopy(text, successCallback);
        });
      } else {
        fallbackCopy(text, successCallback);
      }
    };

    const fallbackCopy = (text, successCallback) => {
      try {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        if (successCallback) successCallback();
      } catch (e) {}
    };

    const copyRichCitation = (apaText, htmlOverride, successCallback) => {
      if (!apaText) return;
      if (typeof htmlOverride === "function") {
        successCallback = htmlOverride;
        htmlOverride = null;
      }
      const rawHtml = htmlOverride ? (htmlOverride.startsWith("<p") ? htmlOverride : `<p style="font-family: 'Times New Roman', Times, serif; font-size: 14pt; color: #000000; line-height: 1.5; margin: 0; padding: 0;">${htmlOverride}</p>`) : apaToHtmlFormatted(apaText);
      const plainText = apaToPlainText(apaText);

      if (navigator.clipboard && window.ClipboardItem && navigator.clipboard.write) {
        try {
          const htmlBlob = new Blob([rawHtml], { type: "text/html" });
          const textBlob = new Blob([plainText], { type: "text/plain" });
          const item = new ClipboardItem({
            "text/html": htmlBlob,
            "text/plain": textBlob
          });
          navigator.clipboard.write([item]).then(() => {
            if (successCallback) successCallback();
          }).catch(() => {
            fallbackRichCopy(rawHtml, plainText, successCallback);
          });
          return;
        } catch (e) {}
      }
      fallbackRichCopy(rawHtml, plainText, successCallback);
    };

    const fallbackRichCopy = (htmlStr, plainStr, successCallback) => {
      try {
        const container = document.createElement("div");
        container.innerHTML = htmlStr;
        container.setAttribute("contenteditable", "true");
        container.style.position = "fixed";
        container.style.left = "-9999px";
        container.style.top = "0";
        container.style.opacity = "0";
        container.style.pointerEvents = "none";
        document.body.appendChild(container);

        const range = document.createRange();
        range.selectNodeContents(container);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);

        const ok = document.execCommand("copy");
        sel.removeAllRanges();
        document.body.removeChild(container);
        if (ok) {
          if (successCallback) successCallback();
          return;
        }
      } catch (e) {}

      fallbackCopy(plainStr, successCallback);
    };

    const handleDoiLookup = async (overrideDoi) => {
      let target = (overrideDoi || doiInput || "").trim();
      if (!target) {
        const el = document.getElementById("doi_input_field") || document.querySelector("input[placeholder*='10.1007']");
        if (el && el.value.trim()) target = el.value.trim();
      }
      if (!target) {
        showAlert(lang === "ar" ? "يرجى إدخال معرّف DOI للبحث" : "Please enter a DOI identifier to lookup", "error");
        return;
      }
      setDoiLoading(true);
      setDoiResult(null);
      setCopiedDoiLink(false);
      setCopiedDoiRaw(false);
      setDoiAbstractExpanded(false);

      const form = new FormData();
      form.append("doi", target);
      if (password) {
        form.append("password", password);
      }

      try {
        const res = await fetch("/api/doi-lookup", {
          method: "POST",
          body: form
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          showAlert(data.error || (lang === "ar" ? "تعذّر استرجاع بيانات معرّف الـ DOI" : "Unable to retrieve DOI metadata"), "error");
        } else {
          setDoiResult(data.paper);
          showAlert(lang === "ar" ? "تم استرجاع بيانات معرّف الـ DOI بنجاح" : "DOI metadata retrieved successfully", "info", 2500);
        }
      } catch (err) {
        showAlert(lang === "ar" ? "تعذّر الاتصال بالسيرفر لفحص معرّف الـ DOI" : "Server connection failed for DOI lookup", "error");
      } finally {
        setDoiLoading(false);
      }
    };

    const handleTitleFindDoi = async (overrideTitle) => {
      let target = (overrideTitle || titleInput || "").trim();
      if (!target) {
        const el = document.getElementById("title_input_field") || document.querySelector("input[placeholder*='Refractory']");
        if (el && el.value.trim()) target = el.value.trim();
      }
      if (!target) {
        showAlert(lang === "ar" ? "يرجى إدخال عنوان البحث" : "Please enter a paper title", "error");
        return;
      }
      setTitleLoading(true);
      setTitleResults([]);
      setCopiedTitleDoiLink(null);
      setCopiedTitleApa(null);

      const form = new FormData();
      form.append("title", target);
      form.append("limit", "10");
      if (password) {
        form.append("password", password);
      }

      try {
        const res = await fetch("/api/find-doi", {
          method: "POST",
          body: form
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          showAlert(data.error || (lang === "ar" ? "تعذّر البحث عن معرّف الـ DOI بالعنوان" : "Unable to find DOI by title"), "error");
        } else {
          setTitleResults(data.results || []);
          if ((data.results || []).length === 0) {
            showAlert(lang === "ar" ? "لم يتم العثور على أبحاث مطابقة للعنوان المدخل" : "No matching papers found for this title", "info", 3000);
          } else {
            showAlert(lang === "ar" ? `تم العثور على ${data.results.length} أبحاث مطابقة بنجاح` : `Found ${data.results.length} matching papers`, "info", 2500);
          }
        }
      } catch (err) {
        showAlert(lang === "ar" ? "تعذّر الاتصال بالسيرفر للبحث بالعنوان" : "Server connection failed for title search", "error");
      } finally {
        setTitleLoading(false);
      }
    };

    
    const handleCheckCardAccess = async (doi, title = "") => {
      if (!doi || cardCheckingMap[doi]) return;
      setCardCheckingMap(prev => ({ ...prev, [doi]: true }));
      try {
        const res = await fetch(`/api/check-access?doi=${encodeURIComponent(doi)}&title=${encodeURIComponent(title || "")}`);
        const data = await res.json();
        if (data.ok && data.access) {
          setCardAccessMap(prev => ({ ...prev, [doi]: data.access }));
        } else {
          setCardAccessMap(prev => ({
            ...prev,
            [doi]: { is_oa: false, oa_url: "", has_scihub: false, scihub_url: "", researchgate: {} }
          }));
        }
      } catch (e) {
        setCardAccessMap(prev => ({
          ...prev,
          [doi]: { is_oa: false, oa_url: "", has_scihub: false, scihub_url: "", researchgate: {} }
        }));
      } finally {
        setCardCheckingMap(prev => ({ ...prev, [doi]: false }));
      }
    };

    const loadHistory = async (silent = false) => {
      setLoadingHistory(true);
      if (!silent) {
        showAlert(lang === "ar" ? "جاري استرجاع الحزم من السجل..." : "Retrieving packages from history...", "info", 2000);
      }

      if (isFileProtocol) {
        setTimeout(() => {
          setLoadingHistory(false);
          if (!silent) showAlert(lang === "ar" ? "وضع المعاينة: تم تحميل بيانات تجريبية" : "Preview mode: Demo data loaded", "info");
          setHistoryList(prev => prev.length ? prev : [
            { filename: "Nanotechnology_Review_2026_PDF.zip", size: "14.2 MB", download_url: "#", pdf_url: "#", at: Date.now() - 3600000, query: "Nanotechnology" },
            { filename: "Machine_Learning_Physics_PDF.zip", size: "9.5 MB", download_url: "#", pdf_url: "#", at: Date.now() - 86400000, query: "Machine Learning" }
          ]);
        }, 400);
        return;
      }

      try {
        const form = new FormData();
        form.append("password", password.trim());
        form.append("guest_token", getOrCreateGuestToken());

        let cachedUhs = [];
        try {
          const cachedStr = localStorage.getItem("ko_guest_uhs");
          if (cachedStr) cachedUhs = JSON.parse(cachedStr);
        } catch(_) {}
        if (Array.isArray(cachedUhs) && cachedUhs.length > 0) {
          form.append("cached_uhs", JSON.stringify(cachedUhs));
        }

        const res = await fetch("/api/history", {
          method: "POST",
          body: form
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || errData.detail || (lang === "ar" ? "فشل جلب السجل" : "Failed to fetch history"));
        }

        const data = await res.json();
        const items = (data.files || data.items || data.history || (Array.isArray(data) ? data : [])).map(item => ({
          filename: item.filename || item.name || (lang === "ar" ? "حزمة بحثية" : "Search Package"),
          size: item.size || "—",
          download_url: item.download_url || item.pdf_url || item.url || "#",
          pdf_url: item.pdf_url || item.download_url || "#",
          at: item.at || item.timestamp || Date.now(),
          timestamp: item.timestamp || "",
          query: item.query || (item.filename ? item.filename.split('_')[0] : ""),
          save_path: item.save_path || item.local_path || "",
          user_hash: item.user_hash || "",
          file_type: item.file_type || ((item.filename || "").toLowerCase().endsWith(".pdf") ? "pdf" : "zip"),
          hours_left: item.hours_left
        }));

        setHistoryList(items);

        // Update known user hashes in localStorage for offline / session continuity
        try {
          const uhSet = new Set(Array.isArray(cachedUhs) ? cachedUhs : []);
          items.forEach(it => { if (it.user_hash) uhSet.add(it.user_hash); });
          localStorage.setItem("ko_guest_uhs", JSON.stringify(Array.from(uhSet).slice(-20)));
        } catch(_) {}

        if (!silent) {
          if (items.length > 0) {
            showAlert(lang === "ar" ? `تم استرجاع ${items.length} حزمة من السجل بنجاح` : `Retrieved ${items.length} packages from history`, "info", 3000);
          } else {
            showAlert(lang === "ar" ? "لا توجد حزم محفوظة حالياً لهذا المعرف/IP" : "No saved packages currently found for this IP/identifier", "info", 3000);
          }
        }
      } catch (err) {
        if (!silent) {
          showAlert(err.message || (lang === "ar" ? "تعذر الاتصال بـ /api/history" : "Unable to connect to /api/history"), "error");
        }
      } finally {
        setLoadingHistory(false);
      }
    };

    const handleLoadSearch = async (item) => {
      try {
        showAlert(lang === "ar" ? `جاري استرجاع نتائج بحث: "${item.query || item.filename}"...` : `Loading results for: "${item.query || item.filename}"...`, "info", 2000);
        const res = await fetch(`/api/history/load?filename=${encodeURIComponent(item.filename)}&user_hash=${encodeURIComponent(item.user_hash || "")}&guest_token=${encodeURIComponent(getOrCreateGuestToken())}`);
        if (!res.ok) {
          throw new Error(lang === "ar" ? "تعذر جلب تفاصيل البحث" : "Unable to fetch search details");
        }
        const jsonRes = await res.json();
        const sData = jsonRes.data || {};

        setQuery(sData.query || item.query || "");
        setResultsPapers(sData.papers || []);
        setDownloadUrl(sData.download_url || item.download_url || "");
        setSavePath(sData.save_path || item.save_path || "");
        setFileType(sData.file_type || item.file_type || "zip");
        setDoneTitle(lang === "ar" ? `نتائج البحث المسترجعة: ${sData.query || item.query}` : `Retrieved Search Results: ${sData.query || item.query}`);

        const nPapers = (sData.papers || []).length;
        if (nPapers > 0) {
          showAlert(lang === "ar" ? `تم استرجاع وعرض (${nPapers}) بحث من السجل بنجاح` : `Loaded (${nPapers}) papers from history`, "success", 3000);
        } else {
          showAlert(lang === "ar" ? `تم فتح سجل البحث بنجاح، يمكنك النقر على "عرض الملف" لفتحه مباشرة` : `Search record loaded. Click "View File" to open package directly.`, "info", 3500);
        }

        setTimeout(() => {
          resultsSectionRef.current?.scrollIntoView({ behavior: "smooth" });
        }, 150);
      } catch (err) {
        showAlert(err.message || (lang === "ar" ? "حدث خطأ أثناء تحميل تفاصيل البحث" : "Error loading search details"), "error");
      }
    };

    const handleDeleteHistory = async (item) => {
      const confirmMsg = lang === "ar" ? `هل أنت متأكد من رغبتك في مسح ملف البحث:\n"${item.query || item.filename}"\nنهائياً من القرص؟` : `Are you sure you want to permanently delete the search file:\n"${item.query || item.filename}"\nfrom disk?`;
      if (!window.confirm(confirmMsg)) return;

      try {
        const res = await fetch("/api/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filename: item.filename, user_hash: item.user_hash || "", password: password.trim(), guest_token: getOrCreateGuestToken() })
        });
        const resData = await res.json().catch(() => ({}));
        if (res.ok && (resData.status === "deleted" || resData.ok)) {
          showAlert(lang === "ar" ? "تم مسح الملف بنجاح من القرص" : "File deleted successfully from disk", "success", 2500);
          setHistoryList(prev => prev.filter(f => f.filename !== item.filename));
          loadHistory();
        } else {
          showAlert(resData.error || resData.detail || (lang === "ar" ? "فشل مسح الملف" : "Failed to delete file"), "error");
        }
      } catch (err) {
        showAlert((lang === "ar" ? "تعذر الاتصال بالسيرفر لمسح الملف: " : "Server connection failed to delete file: ") + err.message, "error");
      }
    };

    const pollTaskStatus = (tid) => {
      if (pollingRef.current) clearInterval(pollingRef.current);

      pollingRef.current = setInterval(async () => {
        try {
          const res = await fetch(`/api/status/${tid}`);
          if (!res.ok) {
            const errText = await res.text();
            throw new Error(errText || (lang === "ar" ? "خطأ أثناء متابعة المهمة" : "Error polling task status"));
          }

          const data = await res.json();
          setProgress(data.progress || 0);
          setStatusMsg(localizeTaskMessage(data.message || data.msg, lang));

          if (data.status === "completed") {
            if (pollingRef.current) clearInterval(pollingRef.current);
            setIsSearching(false);
            setShowDownloadPanel(true);
            setShowModal(true);
            fetchQuota();
            if (data.filename) setFilename(data.filename);

            const finalUrl = data.pdf_url || data.download_url || data.url || "#";
            const finalMd = data.md_url || data.md_zip || "#";
            const isPdf = data.file_type === "pdf" || (data.filename && data.filename.toLowerCase().endsWith(".pdf")) || finalUrl.toLowerCase().includes(".pdf");
            setFileType(isPdf ? "pdf" : "zip");
            setDownloadUrl(finalUrl);
            setMdUrl(finalMd);
            setSavePath(data.save_path || data.local_path || "");
            const isStopped = Boolean(data.counts?.stopped);
            const doneTitleText = isStopped
              ? (lang === "ar" ? `تم الإيقاف — ${data.counts?.peer || 0} بحث محكّم و ${data.counts?.preprints || 0} مسودة` : `Stopped — ${data.counts?.peer || 0} peer-reviewed & ${data.counts?.preprints || 0} preprints`)
              : (lang === "ar" ? `اكتمل — ${data.counts?.peer || 0} بحث محكّم و ${data.counts?.preprints || 0} مسودة` : `Completed — ${data.counts?.peer || 0} peer-reviewed & ${data.counts?.preprints || 0} preprints`);
            setDoneTitle(doneTitleText);

            // Store retrieved papers for live browser
            if (Array.isArray(data.papers) && data.papers.length > 0) {
              setResultsPapers(data.papers);
            }

            const newRecord = {
              filename: data.filename || (isPdf ? `Academic_Report_${query.slice(0, 15)}.pdf` : `Search_${query.slice(0, 15)}_PDF.zip`),
              size: data.size || (isPdf ? "PDF" : "ZIP"),
              download_url: finalUrl,
              pdf_url: finalUrl,
              at: Date.now(),
              timestamp: new Date().toISOString().replace('T', ' ').slice(0, 16),
              query: query,
              save_path: data.save_path || data.local_path || "",
              user_hash: data.user_hash || "",
              file_type: isPdf ? "pdf" : "zip"
            };
            setHistoryList(prev => [newRecord, ...prev]);

            // Save user hash into local storage for continuity
            try {
              if (data.user_hash) {
                let cachedUhs = [];
                try { cachedUhs = JSON.parse(localStorage.getItem("ko_guest_uhs") || "[]"); } catch(_) {}
                if (!Array.isArray(cachedUhs)) cachedUhs = [];
                if (!cachedUhs.includes(data.user_hash)) {
                  cachedUhs.push(data.user_hash);
                  localStorage.setItem("ko_guest_uhs", JSON.stringify(cachedUhs.slice(-20)));
                }
              }
            } catch(_) {}

            // Scroll to results section smoothly after a short delay
            setTimeout(() => {
              if (resultsSectionRef.current) {
                resultsSectionRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            }, 600);

          } else if (data.status === "error" || data.status === "failed") {
            if (pollingRef.current) clearInterval(pollingRef.current);
            setIsSearching(false);
            const failureMessage = data.error || data.message || (lang === "ar" ? "فشلت عملية البحث" : "Search operation failed");
            setStatusMsg(failureMessage);
            setProgress(0);
            setShowDownloadPanel(false);
            showAlert(failureMessage, "error", 9000);
          }
        } catch (err) {
          setStatusMsg(lang === "ar" ? "إعادة محاولة الاتصال بالخادم..." : "Retrying server connection...");
        }
      }, 2000);
    };

    // Reconnect to active running search task when access code is entered or on mount
    useEffect(() => {
      if (activeTaskInfo && activeTaskInfo.has_active_task && activeTaskInfo.task_id) {
        const act = activeTaskInfo;
        if (taskId !== act.task_id || !isSearching) {
          setTaskId(act.task_id);
          setIsSearching(true);
          setShowDownloadPanel(false);
          if (act.query) setQuery(act.query);
          if (act.mode) setMode(act.mode);
          setProgress(act.progress || 10);
          setStatusMsg(localizeTaskMessage(act.message || (lang === "ar" ? "جاري استكمال ومتابعة البحث..." : "Resuming search progress..."), lang));
          pollTaskStatus(act.task_id);
          showAlert(
            lang === "ar"
              ? `🔄 تم رصد بحث جارٍ مرتبط بهذا الرمز ("${act.query || "بحث أكاديمي"}"). جاري عرض التقدم المباشر...`
              : `🔄 Active search detected for this access key ("${act.query || "Academic Search"}"). Live progress active...`,
            "info",
            5000
          );
        }
      }
    }, [activeTaskInfo]);


    const handleSearchSubmit = async (e) => {
      if (e) e.preventDefault();
      if (!query.trim()) {
        showAlert(lang === "ar" ? "يرجى إدخال كلمة أو مصطلح البحث" : "Please enter a search keyword or query", "error");
        if (queryInputRef.current) queryInputRef.current.focus();
        return;
      }

      if (!quota.isVip && dbSource === "elsevier") {
        showAlert(lang === "ar" ? "قاعدة Scopus (Elsevier) غير متاحة للضيوف وتتطلب إدخال مفتاح الوصول (VIP) أو استخدام النسخة المحلية." : "Scopus (Elsevier) is unavailable for guests. VIP key or Local edition required.", "error");
        return;
      }

      showAlert(null);
      setIsSearching(true);
      setShowDownloadPanel(false);
      setResultsPapers([]);
      setProgress(5);
      setStatusMsg(lang === "ar" ? "جاري إرسال الطلب لمحركات البحث الأكاديمية..." : "Sending request to academic search engines...");

      const form = new FormData();
      form.append("password", password.trim());
      form.append("guest_token", getOrCreateGuestToken());
      form.append("query", query.trim());
      form.append("mode", mode);
      form.append("db_source", dbSource);
      form.append("limit", limit);
      form.append("affiliation", affiliation.trim());
      form.append("lang", lang);
      form.append("require_title", requireTitle ? "true" : "false");
      form.append("year_from", yearFrom);
      form.append("year_to", yearTo);
      form.append("include_preprint", includePreprint ? "true" : "false");
      form.append("include_abstracts", includeAbstracts ? "true" : "false");
      form.append("download_fulltext", "false");
      form.append("search_scope", searchScope);
      form.append("doc_type_filter", docTypeFilter);

      try {
        const res = await fetch("/api/search", {
          method: "POST",
          body: form
        });
        fetchQuota();

        const data = await res.json();
        if (!res.ok || data.error) {
          showAlert(data.error || data.detail || (lang === "ar" ? "خطأ في معالجة الطلب" : "Error processing request"), "error");
          setIsSearching(false);
          return;
        }

        const tid = data.task_id || data.id;
        if (!tid) {
          showAlert(lang === "ar" ? "لم يرجع الخادم task_id صالح" : "Server did not return a valid task_id", "error");
          setIsSearching(false);
          return;
        }

        setTaskId(tid);
        setStatusMsg(lang === "ar" ? "بدأت عملية المسح والتجميع والتدقيق المتوازي..." : "Parallel search, aggregation, and verification started...");
        pollTaskStatus(tid);
      } catch (err) {
        showAlert(lang === "ar" ? "تعذر الاتصال بالخادم — تأكد من تشغيل السيرفر" : "Unable to connect to server — please verify backend is running", "error");
        setIsSearching(false);
      }
    };

    const handleCancelTask = async () => {
      if (!taskId) {
        setIsSearching(false);
        if (pollingRef.current) clearInterval(pollingRef.current);
        return;
      }

      if (isFileProtocol) {
        if (pollingRef.current) clearInterval(pollingRef.current);
        setIsSearching(false);
        setStatusMsg(lang === "ar" ? "تم الإلغاء (معاينة)" : "Cancelled (Preview)");
        setProgress(0);
        return;
      }

      try {
        const res = await fetch(`/api/cancel/${taskId}`, { method: "POST" });
        const data = await res.json();
        if (data && data.preserved) {
          showAlert(data.message || (lang === "ar" ? "تم إيقاف البحث — جاري الآن توليد وتجهيز ملف الأبحاث بما تم جمعه..." : "Search stopped — generating document with collected papers..."), "info", 6000);
          setStatusMsg(lang === "ar" ? "تم إيقاف البحث — جاري الآن توليد وتجهيز ملف الأبحاث..." : "Search stopped — generating document with collected papers...");
          return; // Keep polling active until status completes so results & download appear
        }
      } catch (e) {}

      if (pollingRef.current) clearInterval(pollingRef.current);
      setIsSearching(false);
      setStatusMsg(lang === "ar" ? "تم إيقاف البحث بنجاح" : "Search stopped successfully");
      setProgress(0);
      showAlert(lang === "ar" ? "تم إيقاف وإلغاء عملية البحث بناءً على طلبك" : "Search operation stopped as requested", "info", 4000);
    };

    const setYearPreset = (type, fromVal, toVal) => {
      if (type === "all") {
        setYearFrom("");
        setYearTo("");
      } else if (type === "now") {
        setYearFrom(new Date().getFullYear().toString());
        setYearTo("");
      } else if (fromVal) {
        setYearFrom(fromVal);
        setYearTo(toVal || "");
      }
    };

    const toggleAbstract = (idx) => {
      setExpandedAbstracts(prev => ({
        ...prev,
        [idx]: !prev[idx]
      }));
    };

    const handleCopyCitation = (paper, idx, type) => {
      if (type === "bibtex") {
        const text = generateBibTeX(paper);
        copyToClipboard(text, () => {
          setCopiedCiteId(`${idx}_${type}`);
          setTimeout(() => setCopiedCiteId(null), 3000);
        });
      } else {
        const text = generateAPA(paper);
        copyRichCitation(text, paper.apa_html, () => {
          setCopiedCiteId(`${idx}_${type}`);
          setTimeout(() => setCopiedCiteId(null), 3000);
        });
      }
    };

    // Filter papers for results browser
    const filteredPapers = useMemo(() => {
      let list = resultsPapers;
      if (paperFilter === "peer") {
        list = list.filter(p => !p.is_preprint);
      } else if (paperFilter === "preprints") {
        list = list.filter(p => p.is_preprint);
      } else if (paperFilter === "oa") {
        list = list.filter(p => p.is_oa || p.oa_url || p.pdf_url);
      } else if (paperFilter === "review") {
        list = list.filter(p => p.doc_type === "review" || p.doc_type === "meta_analysis" || p.doc_partition === "review");
      } else if (paperFilter === "book") {
        list = list.filter(p => p.doc_type === "book" || p.doc_partition === "book");
      } else if (paperFilter === "research") {
        list = list.filter(p => p.doc_type === "research" || p.doc_partition === "research");
      }

      if (resultsQuery.trim()) {
        const qLower = resultsQuery.trim().toLowerCase();
        list = list.filter(p =>
          (p.title && p.title.toLowerCase().includes(qLower)) ||
          (p.journal && p.journal.toLowerCase().includes(qLower)) ||
          (p.doi && p.doi.toLowerCase().includes(qLower)) ||
          (p.authors && p.authors.some(a => a.toLowerCase().includes(qLower)))
        );
      }
      return list;
    }, [resultsPapers, paperFilter, resultsQuery]);

    // Example search terms chips
    const exampleQueries = [
      "Artificial Intelligence in Healthcare",
      "CRISPR Cas9 Gene Editing",
      "Quantum Computing Algorithms",
      "Renewable Energy Perovskite Solar Cells"
    ];

    return html`
      <div className=${`min-h-screen w-full antialiased ${lang === "ar" ? "font-cairo" : "font-sans"}`} dir=${lang === "ar" ? "rtl" : "ltr"}>
        <!-- Header -->
        <header className="sticky top-0 z-40 border-b border-stone-200/70 dark:border-white/10 glass-panel bg-white/85 dark:bg-[#0c0a09]/85 shadow-sm transition-colors">
          <div className="mx-auto max-w-[1440px] px-3 sm:px-4 md:px-8 h-[64px] sm:h-[68px] flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0">
              <div className="h-9 w-9 sm:h-10 sm:w-10 rounded-[12px] sm:rounded-[14px] bg-[#0c0a09] dark:bg-white text-white dark:text-black grid place-items-center font-sans font-extrabold text-[16px] sm:text-[18px] shadow-sm shrink-0">
                K
              </div>
              <div className="leading-tight min-w-0">
                <div className="font-black text-[14px] sm:text-[16px] tracking-tight font-sans flex items-center gap-1.5 truncate">
                  <span className="truncate">Knowledge Ocean</span>
                  <span className="text-[9px] sm:text-[10px] px-1.5 sm:px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-200 font-mono font-bold shrink-0">${t.appVersion}</span>
                </div>
                <div className="text-[10px] sm:text-[11px] opacity-80 font-semibold truncate hidden sm:block">${t.subtitle}</div>
                <div dir="ltr" className="text-[9px] sm:text-[10px] text-blue-600 dark:text-blue-400 font-bold tracking-wide truncate hidden xs:block">${t.developerCredit}</div>
              </div>
            </div>

            <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
              <!-- Live Guest Quota Badge in Header (Clickable to view/upgrade) -->
              <div
                onClick=${() => {
                  setLoginInputCode(password || "");
                  setLoginError("");
                  setLoginSuccessMsg("");
                  setShowLoginModal(true);
                }}
                class="h-9 sm:h-10 px-2 sm:px-3.5 rounded-[12px] sm:rounded-[14px] border border-stone-200/80 dark:border-white/15 glass-panel bg-white/70 dark:bg-black/40 text-[11px] sm:text-[12px] font-bold flex items-center gap-1.5 sm:gap-2 shadow-sm transition cursor-pointer hover:bg-stone-100 dark:hover:bg-white/10"
                title=${lang === "ar" ? "اضغط لإدارة الحساب أو تسجيل الدخول بالرمز" : "Click to manage account or sign in"}
              >
                ${quota.isVip ? html`
                  <span class="text-amber-500 font-extrabold flex items-center gap-1.5">
                    <span>✨</span>
                    <span class="hidden sm:inline">${t.vipUnlimitedBadge}</span>
                    <span class="sm:hidden">VIP</span>
                  </span>
                ` : (quota.autoRenew || quota.isOther) ? html`
                  <div class="flex items-center gap-1.5 sm:gap-2" title="${lang === 'ar' ? `رصيد يومي متجدد: ${quota.remaining} من 250 بحث (يتجدد يومياً الساعة 12:00 ص بتوقيت بغداد)` : `Daily renewing quota: ${quota.remaining} of 250 searches (Renews daily at 12:00 AM Baghdad time)`}">
                    <span class="w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full bg-teal-500 animate-pulse"></span>
                    <span class="text-teal-700 dark:text-teal-300 font-bold hidden sm:inline">
                      ${lang === 'ar' ? `رصيد يومي: ${quota.remaining} من 250 (${quota.remainingSummary} بملخصات)` : `Daily Quota: ${quota.remaining} / 250 (${quota.remainingSummary} with summaries)`}
                    </span>
                    <span class="text-teal-700 dark:text-teal-300 font-bold sm:hidden font-mono text-[11px]">
                      🔄 ${quota.remaining}/250
                    </span>
                  </div>
                ` : html`
                  <div class="flex items-center gap-1.5 sm:gap-2" title="${lang === 'ar' ? `رصيد البحث المجاني للضيوف: ${quota.remaining} من 50 بحث قياسي (يتجدد يومياً الساعة 12:00 ص بتوقيت بغداد)` : `Guest Quota: ${quota.remaining} of 50 searches (Renews daily at 12:00 AM Baghdad time)`}">
                    <span class=${`w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full ${quota.remaining > 25 ? 'bg-emerald-500' : quota.remaining > 10 ? 'bg-amber-500' : 'bg-rose-500 animate-pulse'}`}></span>
                    <span class="text-stone-700 dark:text-stone-200 font-bold hidden sm:inline">
                      ${lang === 'ar' ? `رصيد الضيوف: ${quota.remaining} من 50 (${quota.remainingSummary} بملخصات)` : `Guest Quota: ${quota.remaining} / 50 (${quota.remainingSummary} with summaries)`}
                    </span>
                    <span class="text-stone-700 dark:text-stone-200 font-bold sm:hidden font-mono text-[11px]">
                      ${quota.remaining}/50
                    </span>
                  </div>
                `}
              </div>

              <!-- Dedicated Sign In / VIP & Secondary Code Button -->
              <button
                id="login-btn"
                type="button"
                onClick=${() => {
                  setLoginInputCode(password || "");
                  setLoginError("");
                  setLoginSuccessMsg("");
                  setShowLoginModal(true);
                }}
                className=${`h-9 sm:h-10 px-2.5 sm:px-3.5 rounded-[12px] sm:rounded-[14px] border transition shadow-sm glass-panel text-[11px] sm:text-[12px] font-bold flex items-center gap-1.5 cursor-pointer ${
                  quota.isVip
                    ? "bg-amber-500/15 dark:bg-amber-500/25 border-amber-500/40 text-amber-700 dark:text-amber-300 hover:bg-amber-500/30"
                    : (quota.autoRenew || quota.isOther)
                    ? "bg-teal-500/15 dark:bg-teal-500/25 border-teal-500/40 text-teal-700 dark:text-teal-300 hover:bg-teal-500/30"
                    : "bg-blue-500/10 dark:bg-blue-500/20 border-blue-500/30 text-blue-700 dark:text-blue-300 hover:bg-blue-500/20"
                }`}
                title=${lang === "ar" ? "تسجيل الدخول بالرمز الثانوي أو مفتاح VIP الأكاديمي" : "Sign in with VIP or Secondary Code"}
              >
                <span className="text-[13px] sm:text-[14px]">${quota.isVip ? "✨" : (quota.autoRenew || quota.isOther) ? "🔄" : "🔑"}</span>
                <span className="hidden sm:inline">
                  ${quota.isVip
                    ? (lang === "ar" ? "حساب VIP" : "VIP Tier")
                    : (quota.autoRenew || quota.isOther)
                    ? (lang === "ar" ? "رمز ثانوي (250)" : "Secondary (250)")
                    : (lang === "ar" ? "تسجيل الدخول" : "Sign In")}
                </span>
                <span className="sm:hidden text-[10px]">
                  ${quota.isVip ? "VIP" : (quota.autoRenew || quota.isOther) ? "250" : (lang === "ar" ? "دخول" : "Login")}
                </span>
              </button>

              <!-- Language Switcher Button (Globe Icon 🌐) -->
              <button
                id="lang-toggle"
                type="button"
                onClick=${() => setLang(lang === "en" ? "ar" : "en")}
                className="h-9 sm:h-10 px-2 sm:px-3 rounded-[12px] sm:rounded-[14px] border border-stone-200 dark:border-white/15 hover:bg-stone-100 dark:hover:bg-white/10 transition shadow-sm glass-panel bg-white/70 dark:bg-black/40 text-[11px] sm:text-[12px] font-bold flex items-center gap-1 cursor-pointer text-stone-800 dark:text-stone-200"
                title=${t.langSwitchTooltip}
                aria-label="Toggle Language"
              >
                <span className="text-[15px] sm:text-[17px]">🌐</span>
                <span className="font-bold tracking-wide text-[10px] sm:text-[11px] uppercase">${t.langTargetLabel}</span>
              </button>

              <button
                id="theme-toggle"
                type="button"
                onClick=${() => setIsDark(!isDark)}
                className="h-9 w-9 sm:h-10 sm:w-10 rounded-full border border-stone-200 dark:border-white/15 grid place-items-center hover:bg-stone-100 dark:hover:bg-white/10 transition shadow-sm glass-panel bg-white/50 dark:bg-black/20 shrink-0"
                aria-label="Toggle Theme"
                title=${isDark ? t.themeLightTooltip : t.themeDarkTooltip}
              >
                <span className="text-[14px] sm:text-[16px]">${isDark ? "☀️" : "🌙"}</span>
              </button>
            </div>
          </div>
        </header>

        <!-- Navigation Switcher (Main Explorer vs. Dedicated Academic DOI Hub) -->
        <div className="mx-auto max-w-[1440px] px-3 sm:px-4 md:px-8 pt-3 sm:pt-4">
          <div className="grid grid-cols-2 sm:inline-flex w-full sm:w-auto p-1 sm:p-1.5 rounded-[18px] sm:rounded-[22px] bg-white/90 dark:bg-stone-900/90 border border-stone-200/90 dark:border-white/15 shadow-md glass-panel gap-1.5 sm:gap-2.5 items-stretch">
            <button
              type="button"
              onClick=${() => setActiveNavTab("explorer")}
              className=${`justify-center px-2.5 sm:px-5 py-2.5 rounded-[14px] sm:rounded-[16px] font-bold text-[12px] sm:text-[13px] transition flex items-center gap-1.5 sm:gap-2 text-center ${
                activeNavTab === "explorer"
                  ? "bg-stone-900 text-white dark:bg-white dark:text-stone-950 shadow-md font-black ring-1 ring-stone-800 dark:ring-white"
                  : "text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-white/10 opacity-80 hover:opacity-100"
              }`}
            >
              <span className="text-sm sm:text-base shrink-0">🌊</span>
              <span className="leading-tight">${t.tabExplorer}</span>
            </button>
            <button
              type="button"
              onClick=${() => setActiveNavTab("doi_hub")}
              className=${`justify-center px-2.5 sm:px-5 py-2.5 rounded-[14px] sm:rounded-[16px] font-bold text-[12px] sm:text-[13px] transition flex items-center gap-1.5 sm:gap-2 text-center ${
                activeNavTab === "doi_hub"
                  ? "bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-700 text-white shadow-lg shadow-blue-500/25 ring-2 ring-blue-400/50 font-black"
                  : "bg-gradient-to-r from-blue-50/90 via-indigo-50/75 to-blue-50/90 dark:from-blue-950/60 dark:via-indigo-950/40 dark:to-blue-950/60 border-2 border-blue-400/70 dark:border-blue-500/50 text-blue-700 dark:text-blue-200 hover:border-blue-500 dark:hover:border-blue-400 hover:bg-blue-100/80 dark:hover:bg-blue-900/60 shadow-sm"
              }`}
            >
              <span className="text-sm sm:text-base shrink-0">🎯</span>
              <span className="leading-tight">${t.tabDoiHub}</span>
              <span className=${`hidden sm:inline-flex text-[9px] sm:text-[10px] px-2 py-0.5 rounded-full font-black tracking-wide items-center gap-1 shrink-0 ${
                activeNavTab === "doi_hub"
                  ? "bg-amber-400 text-stone-950 shadow-sm"
                  : "bg-amber-400 text-stone-950 shadow-sm animate-pulse"
              }`}>
                <span>${t.instantLookupBadge}</span>
              </span>
            </button>
          </div>
        </div>

        <!-- Alert Notification -->
        ${alertInfo.text ? html`
          <div className="mx-auto max-w-[1440px] px-4 md:px-8 mt-4 transition-all animate-fade-in">
            <div className=${`rounded-[16px] px-5 py-3.5 text-[13px] font-bold border flex items-center justify-between shadow-sm glass-panel ${
              alertInfo.type === "error"
                ? "bg-red-50/90 border-red-200 text-red-700 dark:bg-red-950/80 dark:border-red-900 dark:text-red-200"
                : "bg-blue-50/90 border-blue-200 text-blue-700 dark:bg-blue-950/80 dark:border-blue-900 dark:text-blue-200"
            }`}>
              <span>${alertInfo.text}</span>
              <button onClick=${() => setAlertInfo({ text: null, type: "error" })} className="opacity-70 hover:opacity-100 text-[14px] px-2">✕</button>
            </div>
          </div>
        ` : null}

        <!-- Main Grid -->
        <main className="mx-auto max-w-[1440px] px-3 sm:px-4 md:px-8 py-4 sm:py-6 md:py-8 grid grid-cols-12 gap-4 sm:gap-6">
          ${activeNavTab === "doi_hub" ? html`
            <section className="col-span-12">
              <div className=${`rounded-[24px] border ${isDark ? "bg-[#141210]/90 border-white/10" : "bg-white/95 border-stone-200/90"} glass-panel shadow-[0_12px_40px_rgba(0,0,0,0.12)] p-6 md:p-8 space-y-6`}>
                
                <!-- Hub Header -->
                <div className="flex items-center justify-between flex-wrap gap-4 pb-5 border-b border-stone-200/70 dark:border-white/10">
                  <div className="space-y-1">
                    <div className="flex items-center gap-3 flex-wrap">
                      <h2 className="text-[17px] sm:text-[20px] font-black flex items-center gap-2 text-stone-900 dark:text-white flex-wrap">
                        <span className="text-xl sm:text-2xl">🎯</span>
                        <span>${t.doiHubTitle}</span>
                        <span dir="ltr" className="text-[11px] sm:text-[13px] font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/60 px-2.5 py-0.5 rounded-full border border-blue-200 dark:border-blue-800">
                          DOI & Citations
                        </span>
                      </h2>
                      <button
                        type="button"
                        onClick=${() => setActiveNavTab("explorer")}
                        className="px-3.5 py-1.5 rounded-[12px] border border-stone-300 dark:border-white/20 bg-stone-100 hover:bg-stone-200 dark:bg-white/10 dark:hover:bg-white/20 font-bold text-[12px] transition flex items-center gap-1.5 shadow-sm"
                      >
                        <span>🌊 ${t.returnToExplorer}</span>
                      </button>
                    </div>
                    <p className="text-[11.5px] sm:text-[12px] opacity-75 leading-relaxed max-w-[850px]">
                      ${t.doiHubSubtitle}
                    </p>
                  </div>

                  <!-- Sub-tabs Switcher -->
                  <div className="grid grid-cols-2 sm:inline-flex items-center gap-1 bg-stone-100 dark:bg-white/5 p-1 rounded-[14px] text-[12px] sm:text-[13px] font-bold w-full sm:w-auto">
                    <button
                      type="button"
                      onClick=${() => setDoiTab("doi")}
                      className=${`w-full sm:w-auto px-3 sm:px-4 py-2 rounded-[10px] transition flex items-center justify-center gap-1.5 ${
                        doiTab === "doi"
                          ? "bg-white dark:bg-stone-800 text-blue-600 dark:text-blue-400 shadow-sm"
                          : "opacity-70 hover:opacity-100"
                      }`}
                    >
                      <span>🔍</span>
                      <span>${t.doiSubtabDirect}</span>
                    </button>
                    <button
                      type="button"
                      onClick=${() => setDoiTab("title")}
                      className=${`w-full sm:w-auto px-3 sm:px-4 py-2 rounded-[10px] transition flex items-center justify-center gap-1.5 ${
                        doiTab === "title"
                          ? "bg-white dark:bg-stone-800 text-blue-600 dark:text-blue-400 shadow-sm"
                          : "opacity-70 hover:opacity-100"
                      }`}
                    >
                      <span>📑</span>
                      <span>${t.doiSubtabTitle}</span>
                    </button>
                  </div>
                </div>

                <!-- Content for Sub-Tab 1: DOI Lookup -->
                ${doiTab === "doi" ? html`
                  <div className="space-y-6">
                    <div>
                      <label className="text-[13px] font-bold opacity-80 mb-2 block">
                        ${t.doiInputLabel}
                      </label>
                      <div className="flex gap-2.5 flex-col sm:flex-row">
                        <div className="relative flex-1">
                          <input
                            id="doi_input_field"
                            type="text"
                            value=${doiInput}
                            onChange=${(e) => setDoiInput(e.target.value)}
                            onKeyDown=${(e) => { if (e.key === "Enter") handleDoiLookup(); }}
                            placeholder=${t.doiInputPlaceholder}
                            className="w-full h-[50px] rounded-[14px] border border-stone-200 dark:border-white/15 bg-white/70 dark:bg-black/30 px-4 text-[14px] font-mono outline-none focus:border-blue-500 transition"
                            dir="ltr"
                          />
                        </div>
                        <button
                          type="button"
                          onClick=${() => handleDoiLookup()}
                          disabled=${doiLoading}
                          className="h-[50px] px-6 rounded-[14px] bg-blue-600 hover:bg-blue-700 text-white font-bold text-[13px] transition flex items-center justify-center gap-2 shadow-sm disabled:opacity-50 shrink-0"
                        >
                          <span>${doiLoading ? t.doiLookupLoading : t.doiLookupBtn}</span>
                        </button>
                      </div>

                      <div className="mt-3 flex items-center gap-2 flex-wrap">
                        <span className="text-[11px] opacity-60 font-bold">${t.doiExamplesLabel}</span>
                        <button
                          type="button"
                          onClick=${() => { setDoiInput("10.1007/s40278-024-60584-4"); handleDoiLookup("10.1007/s40278-024-60584-4"); }}
                          className="text-[11px] px-3 py-1 rounded-full border border-stone-200 dark:border-white/10 hover:border-blue-500 bg-white/50 dark:bg-white/5 font-mono"
                          dir="ltr"
                        >
                          10.1007/s40278-024-60584-4
                        </button>
                        <button
                          type="button"
                          onClick=${() => { setDoiInput("10.1186/s13256-025-05459-w"); handleDoiLookup("10.1186/s13256-025-05459-w"); }}
                          className="text-[11px] px-3 py-1 rounded-full border border-stone-200 dark:border-white/10 hover:border-blue-500 bg-white/50 dark:bg-white/5 font-mono"
                          dir="ltr"
                        >
                          10.1186/s13256-025-05459-w
                        </button>
                      </div>
                    </div>

                    ${doiResult ? html`
                      <div className="rounded-[20px] border border-blue-200 dark:border-blue-900/60 bg-blue-50/30 dark:bg-blue-950/20 p-6 space-y-5 animate-fade-in">
                        
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className=${`text-[11px] px-3 py-1 rounded-full font-bold border ${
                              doiResult.is_preprint
                                ? "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-300 dark:border-amber-800"
                                : "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800"
                            }`}>
                              ${doiResult.is_preprint ? t.preprint : t.peerReviewed}
                            </span>

                            ${doiResult.year && doiResult.year !== "0000" ? html`
                              <span className="text-[11px] px-2.5 py-1 rounded-full bg-stone-100 dark:bg-white/10 font-sans font-bold">
                                ${doiResult.year}
                              </span>
                            ` : null}

                            ${doiResult.is_oa ? html`
                              <span className="text-[11px] px-2.5 py-1 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 font-bold border border-blue-200 dark:border-blue-800">
                                🔓 Open Access
                              </span>
                            ` : null}

                            ${doiResult.citation_count > 0 ? html`
                              <span className="text-[11px] px-2.5 py-1 rounded-full bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300 font-sans font-bold">
                                ★ ${doiResult.citation_count} ${t.citationsCount}
                              </span>
                            ` : null}
                          </div>

                          <div className="text-[11px] opacity-60 font-mono">
                            ${t.sourcesLabel} ${(doiResult.sources || []).join(" · ")}
                          </div>
                        </div>

                        <h3 className="text-[18px] font-black text-stone-950 dark:text-stone-50 leading-snug" dir="ltr">
                          ${doiResult.title}
                        </h3>

                        <div className="text-[13px] space-y-1" dir="ltr">
                          <div className="font-semibold opacity-90">
                            👤 ${(doiResult.authors && doiResult.authors.length) ? doiResult.authors.join(", ") : "Unknown Authors"}
                          </div>
                          ${doiResult.journal ? html`
                            <div className="italic opacity-75">
                              📖 ${doiResult.journal} ${doiResult.publisher ? `(${doiResult.publisher})` : ""}
                            </div>
                          ` : null}
                        </div>

                        <div className="rounded-[16px] bg-white dark:bg-stone-900 border border-blue-200 dark:border-blue-800 p-4 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                          <div className="space-y-1">
                            <div className="text-[11px] font-bold text-blue-600 dark:text-blue-400">
                              ${lang === "ar" ? "رابط الـ DOI المباشر والمعتمد أكاديمياً:" : "Direct & Verified Scholarly DOI URL:"}
                            </div>
                            <div className="font-mono text-[14px] font-black text-stone-900 dark:text-white break-all select-all" dir="ltr">
                              ${doiResult.doi_url}
                            </div>
                          </div>

                          <div className="flex items-center gap-2 flex-wrap shrink-0">
                            <button
                              type="button"
                              onClick=${() => {
                                copyToClipboard(doiResult.doi_url, () => {
                                  setCopiedDoiLink(true);
                                  setTimeout(() => setCopiedDoiLink(false), 2500);
                                });
                              }}
                              className=${`h-[38px] px-4 rounded-[10px] font-bold text-[12px] transition flex items-center gap-1.5 shadow-sm ${
                                copiedDoiLink
                                  ? "bg-emerald-600 text-white"
                                  : "bg-blue-600 hover:bg-blue-700 text-white"
                              }`}
                              title=${lang === "ar" ? "نسخ رابط الـ DOI كاملاً لمشاركته أو توثيقه" : "Copy full DOI link for sharing or citation"}
                            >
                              <span>${copiedDoiLink ? t.copyDoiLinkDone : t.copyDoiLinkBtn}</span>
                            </button>

                            <button
                              type="button"
                              onClick=${() => {
                                copyToClipboard(doiResult.doi, () => {
                                  setCopiedDoiRaw(true);
                                  setTimeout(() => setCopiedDoiRaw(false), 2500);
                                });
                              }}
                              className="h-[38px] px-3.5 rounded-[10px] border border-stone-300 dark:border-white/20 bg-stone-100 hover:bg-stone-200 dark:bg-white/10 dark:hover:bg-white/20 font-bold text-[12px] transition flex items-center gap-1"
                              title=${lang === "ar" ? "نسخ المعرف المجرد فقط" : "Copy raw DOI identifier only"}
                            >
                              <span>${copiedDoiRaw ? (lang === "ar" ? "✓ تم النسخ" : "✓ Copied") : (lang === "ar" ? "نسخ DOI فقط" : "Copy DOI Only")}</span>
                            </button>

                            <a
                              href=${doiResult.doi_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="h-[38px] px-3.5 rounded-[10px] border border-stone-300 dark:border-white/20 bg-stone-100 hover:bg-stone-200 dark:bg-white/10 dark:hover:bg-white/20 font-bold text-[12px] transition flex items-center gap-1"
                            >
                              <span>↗ ${lang === "ar" ? "فتح الرابط" : "Open Link"}</span>
                            </a>
                          </div>
                        </div>

                        ${doiResult.apa ? html`
                          <div className="rounded-[16px] bg-purple-50/70 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-800/60 p-4 shadow-sm space-y-2.5">
                            <div className="flex items-center justify-between flex-wrap gap-2">
                              <div className="text-[12px] font-black text-purple-900 dark:text-purple-300 flex items-center gap-1.5">
                                <span>📜</span>
                                <span>${lang === "ar" ? "توثيق APA 7th القياسي الصارم (جاهز للنسخ إلى Microsoft Word):" : "Strict APA 7th Citation (Ready to paste into Word):"}</span>
                              </div>

                              <button
                                type="button"
                                onClick=${() => {
                                  copyRichCitation(doiResult.apa, doiResult.apa_html, () => {
                                    setCopiedDoiApa(true);
                                    showAlert(lang === "ar" ? "تم نسخ توثيق APA 7th للوورد بنجاح (المجلة مائلة والمجلد عريض وبدون نجوم)!" : "APA 7th citation copied for Word (Journal italicized, Volume bold, No asterisks)!", "success", 2500);
                                    setTimeout(() => setCopiedDoiApa(false), 2500);
                                  });
                                }}
                                className=${`h-[34px] px-3.5 rounded-[10px] font-bold text-[12px] transition flex items-center gap-1.5 shadow-sm ${
                                  copiedDoiApa
                                    ? "bg-emerald-600 text-white"
                                    : "bg-purple-600 hover:bg-purple-700 text-white"
                                }`}
                                title=${lang === "ar" ? "نسخ التوثيق بالصيغة الغنية للصقه مباشرة في Microsoft Word أو الأبحاث" : "Copy formatted citation ready to paste into Microsoft Word"}
                              >
                                <span>${copiedDoiApa ? (lang === "ar" ? "✓ تم النسخ للوورد" : "✓ Copied for Word") : (lang === "ar" ? "📋 نسخ للوورد (Word)" : "📋 Copy for Word")}</span>
                              </button>
                            </div>

                            <div
                              className="text-[15px] leading-relaxed text-stone-900 dark:text-stone-100 select-all p-3 rounded-[10px] bg-white/80 dark:bg-stone-900/70 border border-purple-100 dark:border-purple-900/40"
                              style="font-family: 'Times New Roman', Times, serif; font-size: 14pt;"
                              dir="ltr"
                              dangerouslySetInnerHTML=${{
                                __html: doiResult.apa_html || apaToHtmlFormatted(doiResult.apa)
                              }}
                            />
                          </div>
                        ` : null}

                        ${doiResult.abstract ? html`
                          <div className="pt-2 border-t border-stone-200/50 dark:border-white/5">
                            <div className="text-[12px] font-bold opacity-80 mb-1">${lang === "ar" ? "ملخص البحث (Abstract):" : "Paper Abstract:"}</div>
                            <p className=${`text-[13px] leading-relaxed text-stone-700 dark:text-stone-300 ${!doiAbstractExpanded ? "line-clamp-3" : ""}`} dir="ltr">
                              ${doiResult.abstract}
                            </p>
                            <button
                              type="button"
                              onClick=${() => setDoiAbstractExpanded(!doiAbstractExpanded)}
                              className="mt-1.5 text-[11px] font-bold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
                            >
                              ${doiAbstractExpanded ? (lang === "ar" ? "إخفاء الملخص ▴" : "Hide Abstract ▴") : (lang === "ar" ? "قراءة الملخص كاملاً ▾" : "Read Full Abstract ▾")}
                            </button>
                          </div>
                        ` : null}

                        <div className="pt-3 flex items-center justify-between flex-wrap gap-3 border-t border-stone-200/50 dark:border-white/5">
                          <div className="flex items-center gap-2 flex-wrap">
                            ${doiResult.oa_url ? html`
                              <a
                                href=${doiResult.oa_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="h-[36px] px-4 rounded-[10px] bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[12px] transition flex items-center gap-1.5 shadow-sm"
                              >
                                <span>${t.downloadFullOa}</span>
                              </a>
                            ` : html`
                              <span className="text-[12px] opacity-60">
                                ${t.publisherSubNotice}
                              </span>
                            `}

                            <!-- Sci-Hub Verification & Search Button (Permanent) -->
                            ${(() => {
                              const shConfirmed = doiResult.has_scihub && doiResult.scihub_url;
                              const shUrl = doiResult.scihub_url || `https://sci-hub.ren/${doiResult.doi || ""}`;
                              return html`
                                <a
                                  href=${shUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className=${`h-[36px] px-3 rounded-[10px] font-bold text-[12px] transition flex items-center gap-1.5 shadow-sm ${
                                    shConfirmed
                                      ? "bg-amber-600 hover:bg-amber-700 text-white"
                                      : "bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60 hover:bg-amber-100 dark:hover:bg-amber-900/60"
                                  }`}
                                  title=${shConfirmed ? t.scihubConfirmedBtn : t.scihubSearchTitle}
                                >
                                  <span>🔓</span>
                                  <span>${shConfirmed ? t.scihubConfirmedBtn : t.scihubSearchBtn}</span>
                                </a>
                              `;
                            })()}

                            <!-- ResearchGate Verification & Download Button -->
                            ${(() => {
                              const rg = doiResult.researchgate || {};
                              const rgUrl = rg.download_url || rg.url || `https://www.researchgate.net/search/publication?q=${encodeURIComponent(doiResult.doi || doiResult.title)}`;
                              const hasDl = rg.has_download;
                              return html`
                                <a
                                  href=${rgUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className=${`h-[36px] px-3 rounded-[10px] font-bold text-[12px] transition flex items-center gap-1.5 shadow-sm ${
                                    hasDl
                                      ? "bg-teal-600 hover:bg-teal-700 text-white"
                                      : "bg-teal-50 dark:bg-teal-950/50 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800/60 hover:bg-teal-100 dark:hover:bg-teal-900/60"
                                  }`}
                                  title=${hasDl ? t.rgDownloadBtn : t.rgSearchTitle}
                                >
                                  <span>🔬</span>
                                  <span>${hasDl ? t.rgDownloadBtn : t.rgSearchBtn}</span>
                                </a>
                              `;
                            })()}


                          </div>

                          <div className="flex items-center gap-2">
                            ${doiResult.apa ? html`
                              <button
                                type="button"
                                onClick=${() => {
                                  copyRichCitation(doiResult.apa, doiResult.apa_html, () => showAlert(lang === "ar" ? "تم نسخ توثيق APA 7th منسقاً للوورد (مائل وعريض بدون نجوم)" : "Formatted APA 7th citation copied for Word (Italics & Bold, no asterisks)", "success", 2500));
                                }}
                                className="px-3 py-1.5 rounded-[8px] bg-purple-50 hover:bg-purple-100 dark:bg-purple-950/40 dark:hover:bg-purple-900/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/60 font-bold text-[11px] transition flex items-center gap-1 shadow-sm"
                                title=${doiResult.apa_plain || apaToPlainText(doiResult.apa)}
                              >
                                📋 APA 7th
                              </button>
                            ` : null}
                            <button
                              type="button"
                              onClick=${() => {
                                copyToClipboard(doiResult.bibtex, () => showAlert(lang === "ar" ? "تم نسخ توثيق BibTeX بنجاح" : "BibTeX citation copied successfully", "info", 2000));
                              }}
                              className="px-3 py-1.5 rounded-[8px] bg-stone-100 hover:bg-stone-200 dark:bg-white/10 dark:hover:bg-white/20 font-bold text-[11px] font-mono transition cursor-pointer"
                            >
                              ${lang === "ar" ? "توثيق BibTeX" : "BibTeX Citation"}
                            </button>
                            ${(doiResult.bibtex_download_url || doiResult.doi) ? html`
                              <a
                                href=${doiResult.bibtex_download_url || `/api/download-bibtex?doi=${encodeURIComponent(doiResult.doi)}`}
                                download
                                className="px-3 py-1.5 rounded-[8px] bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/40 dark:hover:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 font-bold text-[11px] font-mono transition flex items-center gap-1 shadow-sm"
                                title=${lang === "ar" ? "تنزيل ملف BibTeX (.bib) مباشرة" : "Download BibTeX (.bib) file"}
                              >
                                ⬇️ .bib
                              </a>
                            ` : null}
                          </div>
                        </div>

                      </div>
                    ` : null}

                  </div>
                ` : html`
                  <div className="space-y-6">
                    <div>
                      <label className="text-[13px] font-bold opacity-80 mb-2 block">
                        ${lang === "ar" ? "أدخل عنوان البحث العلمي كاملاً أو جزءاً منه لإيجاد معرّف DOI المطابق" : "Enter full or partial paper title to find matching DOI"}
                      </label>
                      <div className="flex gap-2.5 flex-col sm:flex-row">
                        <div className="relative flex-1">
                          <input
                            id="title_input_field"
                            type="text"
                            value=${titleInput}
                            onChange=${(e) => setTitleInput(e.target.value)}
                            onKeyDown=${(e) => { if (e.key === "Enter") handleTitleFindDoi(); }}
                            placeholder=${lang === "ar" ? "مثال: Refractory high anion gap metabolic acidosis due to chronic paracetamol..." : "e.g. Refractory high anion gap metabolic acidosis due to chronic paracetamol..."}
                            className="w-full h-[50px] rounded-[14px] border border-stone-200 dark:border-white/15 bg-white/70 dark:bg-black/30 px-4 text-[14px] outline-none focus:border-blue-500 transition"
                            dir="ltr"
                          />
                        </div>
                        <button
                          type="button"
                          onClick=${() => handleTitleFindDoi()}
                          disabled=${titleLoading}
                          className="h-[50px] px-6 rounded-[14px] bg-blue-600 hover:bg-blue-700 text-white font-bold text-[13px] transition flex items-center justify-center gap-2 shadow-sm disabled:opacity-50 shrink-0"
                        >
                          <span>${titleLoading ? (lang === "ar" ? "جاري البحث..." : "Searching...") : (lang === "ar" ? "استخراج الـ DOI بالعنوان 🎯" : "Match Title to DOI 🎯")}</span>
                        </button>
                      </div>

                      <div className="mt-3 flex items-center gap-2 flex-wrap">
                        <span className="text-[11px] opacity-60 font-bold">${lang === "ar" ? "أمثلة عناوين للتجربة:" : "Sample titles to try:"}</span>
                        <button
                          type="button"
                          onClick=${() => {
                            const t = "Refractory high anion gap metabolic acidosis due to chronic paracetamol";
                            setTitleInput(t);
                            handleTitleFindDoi(t);
                          }}
                          className="text-[11px] px-3 py-1 rounded-full border border-stone-200 dark:border-white/10 hover:border-blue-500 bg-white/50 dark:bg-white/5 font-sans"
                          dir="ltr"
                        >
                          Refractory high anion gap metabolic acidosis...
                        </button>
                        <button
                          type="button"
                          onClick=${() => {
                            const t = "Laser-induced porous graphene electrodes from polyketimine membranes";
                            setTitleInput(t);
                            handleTitleFindDoi(t);
                          }}
                          className="text-[11px] px-3 py-1 rounded-full border border-stone-200 dark:border-white/10 hover:border-blue-500 bg-white/50 dark:bg-white/5 font-sans"
                          dir="ltr"
                        >
                          Laser-induced porous graphene electrodes...
                        </button>
                      </div>
                    </div>

                    ${titleResults && titleResults.length > 0 ? html`
                      <div className="space-y-4 animate-fade-in">
                        <div className="text-[14px] font-black text-stone-900 dark:text-stone-100 flex items-center gap-2">
                          <span>${lang === "ar" ? "الأبحاث المطابقة المستخرجة:" : "Matching papers found:"}</span>
                          <span className="text-[11px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 font-bold">
                            ${titleResults.length} ${lang === "ar" ? "نتائج" : "results"}
                          </span>
                        </div>

                        <div className="space-y-3">
                          ${titleResults.map((item, idx) => html`
                            <div
                              key=${idx}
                              className="rounded-[18px] border border-stone-200 dark:border-white/10 bg-white/80 dark:bg-stone-900/60 p-4 shadow-sm hover:border-blue-300 transition space-y-2.5"
                            >
                              <div className="flex items-center justify-between flex-wrap gap-2">
                                <span className=${`text-[11px] px-2.5 py-0.5 rounded-full font-bold border ${
                                  item.similarity >= 88
                                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-300 shadow-sm"
                                    : item.similarity >= 70
                                    ? "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300 border-blue-300"
                                    : "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border-amber-300"
                                }`}>
                                  ${item.similarity >= 95 ? "✨ " : ""}${lang === "ar" ? `نسبة تطابق العنوان: ${item.similarity}%` : `Title Match Confidence: ${item.similarity}%`}
                                </span>

                                <div className="text-[11px] opacity-60 font-mono">
                                  ${item.year !== "0000" ? item.year : ""} · ${item.source}
                                </div>
                              </div>

                              <h4 className="text-[14px] font-black leading-snug" dir="ltr">
                                ${item.title}
                              </h4>

                              <div className="text-[12px] opacity-75 space-y-0.5" dir="ltr">
                                <div className="truncate">👤 ${(item.authors || []).join(", ")}</div>
                                ${item.journal ? html`<div className="italic">📖 ${item.journal}</div>` : null}
                              </div>

                              <div className="pt-2 flex items-center justify-between flex-wrap gap-2 border-t border-stone-100 dark:border-white/5">
                                <div className="flex items-center gap-2 font-mono text-[12px] font-bold text-blue-600 dark:text-blue-400 break-all" dir="ltr">
                                  <span>🔗</span> ${item.doi_url}
                                </div>

                                <div className="flex items-center gap-1.5 flex-wrap">
                                  ${(item.doi_url || item.oa_url) ? html`
                                    <button
                                      type="button"
                                      onClick=${() => {
                                        copyToClipboard(item.doi_url || item.oa_url, () => {
                                          setCopiedTitleDoiLink(idx);
                                          setTimeout(() => setCopiedTitleDoiLink(null), 2000);
                                        });
                                      }}
                                      className=${`h-[32px] px-3 rounded-[8px] font-bold text-[11px] transition flex items-center gap-1 shadow-sm ${
                                        copiedTitleDoiLink === idx
                                          ? "bg-emerald-600 text-white"
                                          : "bg-blue-600 hover:bg-blue-700 text-white"
                                      }`}
                                      title=${lang === "ar" ? (item.doi ? "نسخ رابط الـ DOI كاملاً" : "نسخ رابط البحث المباشر") : (item.doi ? "Copy full DOI link" : "Copy publication link")}
                                    >
                                      <span>${copiedTitleDoiLink === idx ? (lang === "ar" ? "تم النسخ ✓" : "Copied ✓") : (item.doi ? t.copyDoiLinkBtn : (lang === "ar" ? "نسخ الرابط" : "Copy Link"))}</span>
                                    </button>
                                  ` : null}

                                  ${item.apa ? html`
                                    <button
                                      type="button"
                                      onClick=${() => {
                                        copyRichCitation(item.apa, item.apa_html, () => {
                                          setCopiedTitleApa(idx);
                                          showAlert(lang === "ar" ? "تم نسخ توثيق APA 7th للوورد بنجاح" : "APA 7th citation copied for Word", "success", 2000);
                                          setTimeout(() => setCopiedTitleApa(null), 2500);
                                        });
                                      }}
                                      className=${`h-[32px] px-2.5 rounded-[8px] font-bold text-[11px] transition flex items-center gap-1 shadow-sm border ${
                                        copiedTitleApa === idx
                                          ? "bg-emerald-600 border-emerald-600 text-white"
                                          : "bg-purple-50 hover:bg-purple-100 dark:bg-purple-950/40 dark:hover:bg-purple-900/60 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-800/60"
                                      }`}
                                      title=${item.apa_plain || apaToPlainText(item.apa)}
                                    >
                                      <span>${copiedTitleApa === idx ? (lang === "ar" ? "تم نسخ APA ✓" : "Copied APA ✓") : "📋 APA 7th"}</span>
                                    </button>
                                  ` : null}

                                  ${item.doi ? html`
                                    <button
                                      type="button"
                                      onClick=${() => {
                                        copyToClipboard(item.doi, () => showAlert(lang === "ar" ? "تم نسخ معرّف الـ DOI فقط" : "DOI identifier copied", "info", 2000));
                                      }}
                                      className="h-[32px] px-2.5 rounded-[8px] bg-stone-100 hover:bg-stone-200 dark:bg-white/10 dark:hover:bg-white/20 font-bold text-[11px] transition"
                                    >
                                      ${lang === "ar" ? "نسخ DOI" : "Copy DOI"}
                                    </button>

                                    <button
                                      type="button"
                                      onClick=${() => {
                                        setDoiTab("doi");
                                        setDoiInput(item.doi);
                                        handleDoiLookup(item.doi);
                                      }}
                                      className="h-[32px] px-2.5 rounded-[8px] border border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400 font-bold text-[11px] transition"
                                    >
                                      ${t.detailedCheckBtn}
                                    </button>

                                    <a
                                      href=${`https://sci-hub.ren/${item.doi}`}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="h-[32px] px-2.5 rounded-[8px] bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/40 dark:hover:bg-amber-900/60 text-amber-700 dark:text-amber-300 font-bold text-[11px] transition flex items-center gap-1 border border-amber-200 dark:border-amber-800/60"
                                      title=${t.scihubSearchTitle}
                                    >
                                      <span>🔓 Sci-Hub</span>
                                    </a>
                                  ` : html`
                                    <span className="h-[32px] px-2.5 rounded-[8px] bg-stone-100 dark:bg-white/10 text-stone-600 dark:text-stone-300 font-bold text-[11px] flex items-center border border-stone-200 dark:border-white/10">
                                      ${lang === "ar" ? "بدون DOI (متاح بالرابط)" : "No DOI (Available via Link)"}
                                    </span>
                                  `}

                                  <a
                                    href=${item.rg_url || ((item.doi_url && item.doi_url.includes("researchgate.net")) ? item.doi_url : `https://www.researchgate.net/search/publication?q=${encodeURIComponent(item.doi || item.title)}`)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="h-[32px] px-2.5 rounded-[8px] bg-teal-50 hover:bg-teal-100 dark:bg-teal-950/40 dark:hover:bg-teal-900/60 text-teal-700 dark:text-teal-300 font-bold text-[11px] transition flex items-center gap-1 border border-teal-200 dark:border-teal-800/60"
                                    title=${t.rgSearchTitle}
                                  >
                                    <span>🔬 ResearchGate</span>
                                  </a>

                                  ${(item.doi_url || item.oa_url) ? html`
                                    <a
                                      href=${item.doi_url || item.oa_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="h-[32px] px-2.5 rounded-[8px] bg-stone-100 hover:bg-stone-200 dark:bg-white/10 dark:hover:bg-white/20 font-bold text-[11px] transition flex items-center"
                                      title=${lang === "ar" ? "فتح رابط البحث في نافذة جديدة" : "Open link in new tab"}
                                    >
                                      ↗
                                    </a>
                                  ` : null}
                                </div>

                              </div>

                            </div>
                          `)}
                        </div>
                      </div>
                    ` : null}

                  </div>
                `}

              </div>
            </section>
          ` : html`
            <!-- Search Section -->
            <section className="col-span-12 lg:col-span-8">
            

            <form onSubmit=${handleSearchSubmit} className="space-y-6">
              <div className=${`rounded-[20px] sm:rounded-[24px] border ${isDark ? "bg-[#141210]/85 border-white/10" : "bg-white/90 border-stone-200/90"} glass-panel shadow-[0_12px_40px_rgba(0,0,0,0.12)] p-4 sm:p-6 md:p-8`}>
                <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
                  <h2 className="text-[19px] font-black">${t.searchSettingsTitle}</h2>
                  <span className=${`text-[11px] px-3 py-1 rounded-full border font-sans font-bold shadow-sm flex items-center gap-1.5 ${
                    isLocal
                      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800"
                      : "bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-200 border border-blue-200 dark:border-blue-800"
                  }`}>
                    <span className=${isLocal ? "text-emerald-600 dark:text-emerald-400 font-black" : "text-blue-600 dark:text-blue-400 font-black"}>●</span>
                    ${quota.isVip ? (lang === 'ar' ? 'وصول VIP غير محدود ✨' : 'VIP Unlimited Access ✨') : (quota.autoRenew || quota.isOther) ? (lang === 'ar' ? `رصيد متجدد تلقائياً: ${quota.remaining} بحث (${quota.remainingSummary} بملخصات)` : `Auto-Renewing: ${quota.remaining} searches (${quota.remainingSummary} with summaries)`) : (lang === 'ar' ? `رصيد الضيوف: ${quota.remaining} بحث (${quota.remainingSummary} بملخصات)` : `Guest Quota: ${quota.remaining} searches (${quota.remainingSummary} with summaries)`)}
                  </span>
                </div>

                <!-- Search Mode & Operation Status -->
                <div className="grid grid-cols-12 gap-4">
                  ${isLocal ? html`
                    <div className="col-span-12 md:col-span-6">
                      <label className="text-[12px] font-bold opacity-80 mb-1.5 block">${t.operationModeLabel}</label>
                      <div className="flex items-center justify-between h-[46px] rounded-[12px] border border-emerald-300 dark:border-emerald-800/80 bg-emerald-50/60 dark:bg-emerald-950/30 px-3.5 shadow-sm">
                        <span className="text-[13px] font-bold text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
                          <span className="text-emerald-600 dark:text-emerald-400 font-black">⚡</span> ${t.localAccessText}
                        </span>
                        <button
                          type="button"
                          onClick=${() => loadHistory(false)}
                          disabled=${loadingHistory}
                          title=${lang === "ar" ? "عرض الحزم السابقة المستخرجة محلياً" : "View previously extracted local packages"}
                          className="h-[32px] px-3 rounded-[10px] bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-[11px] transition flex items-center gap-1 shrink-0 shadow-sm disabled:opacity-50"
                        >
                          <span>${loadingHistory ? t.historyBtnLoading : t.historyBtn}</span>
                        </button>
                      </div>
                    </div>
                  ` : null}

                  <div className=${isLocal ? 'col-span-12 md:col-span-6' : 'col-span-12'}>
                    <label className="text-[12px] font-bold opacity-80 mb-1.5 block">${t.searchModeLabel}</label>
                    <select
                      id="mode"
                      value=${mode}
                      onChange=${(e) => {
                        const val = e.target.value;
                        if (val === "doi") {
                          setActiveNavTab("doi_hub");
                          setDoiTab("doi");
                          const currentQ = query.trim();
                          if (currentQ) {
                            setDoiInput(currentQ);
                            if (currentQ.includes("10.") || currentQ.includes("/")) {
                              handleDoiLookup(currentQ);
                            }
                          }
                          showAlert(lang === "ar" ? "تم الانتقال فوراً إلى منظومة التوثيق المرجعي عبر معرّف DOI" : "Navigated to DOI & Citation Resolver", "info", 3000);
                          setTimeout(() => {
                            const inp = document.getElementById("doi_input_field");
                            if (inp) { inp.focus(); inp.select(); }
                          }, 150);
                          return;
                        }
                        if (val === "title_doi") {
                          setActiveNavTab("doi_hub");
                          setDoiTab("title");
                          const currentQ = query.trim();
                          if (currentQ) {
                            setTitleInput(currentQ);
                            handleTitleFindDoi(currentQ);
                          }
                          showAlert(lang === "ar" ? "تم الانتقال فوراً إلى منظومة مطابقة عناوين الأبحاث واستخراج معرّف الـ DOI" : "Navigated to Title-to-DOI Matching", "info", 3000);
                          setTimeout(() => {
                            const inp = document.getElementById("title_input_field");
                            if (inp) { inp.focus(); inp.select(); }
                          }, 150);
                          return;
                        }
                        setMode(val);
                      }}
                      className="w-full h-[46px] rounded-[12px] border border-stone-200 dark:border-white/15 bg-white/70 dark:bg-black/30 px-3.5 text-[14px] outline-none transition cursor-pointer"
                    >
                      <option value="keyword" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.modeKeyword}</option>
                      <option value="author" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.modeAuthor}</option>
                      <option value="exact" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.modeExact}</option>
                      <option value="doi" className="bg-[#fcfaf8] dark:bg-[#1a1816] font-bold text-blue-600 dark:text-blue-400">${t.modeDoi}</option>
                      <option value="title_doi" className="bg-[#fcfaf8] dark:bg-[#1a1816] font-bold text-blue-600 dark:text-blue-400">${t.modeTitleDoi}</option>
                    </select>
                  </div>
                </div>

                <!-- Query Textarea -->
                <div className="mt-5">
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-[12px] font-bold opacity-80 block">${t.queryLabel}</label>
                    <div className="flex items-center gap-2">
                      ${query.trim() ? html`
                        <button
                          type="button"
                          onClick=${() => { setQuery(""); if (queryInputRef.current) queryInputRef.current.focus(); }}
                          className="text-[11px] text-stone-500 hover:text-stone-800 dark:hover:text-stone-200 font-bold transition"
                        >
                          ${t.clearQueryBtn}
                        </button>
                      ` : null}
                      <span className="text-[10px] text-stone-400 font-mono">${lang === "ar" ? "اضغط Ctrl + Enter للبحث السريع" : "Press Ctrl + Enter for quick search"}</span>
                    </div>
                  </div>
                  <div className="relative">
                    <textarea
                      id="query"
                      ref=${queryInputRef}
                      value=${query}
                      onChange=${(e) => setQuery(e.target.value)}
                      onKeyDown=${(e) => {
                        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                          e.preventDefault();
                          handleSearchSubmit();
                        }
                      }}
                      rows=${3}
                      placeholder=${lang === "ar" ? "مثال: Artificial Intelligence AND (Deep Learning OR Neural Networks) أو أدخل معرف DOI مباشر..." : "e.g. Artificial Intelligence AND (Deep Learning OR Neural Networks) or enter direct DOI..."}
                      className="w-full rounded-[16px] border border-stone-200 dark:border-white/15 bg-white/70 dark:bg-black/30 p-4 text-[14px] leading-6 outline-none focus:border-stone-900 dark:focus:border-white resize-none transition"
                      dir="ltr"
                    />
                  </div>

                  <!-- Query Example Chips -->
                  <div className="mt-2.5 flex items-center gap-1.5 flex-wrap">
                    <span className="text-[11px] opacity-60 font-bold">${lang === "ar" ? "أمثلة سريعة:" : "Quick Examples:"}</span>
                    ${exampleQueries.map((ex, i) => html`
                      <button
                        key=${i}
                        type="button"
                        onClick=${() => { setQuery(ex); if (queryInputRef.current) queryInputRef.current.focus(); }}
                        className="text-[11px] px-2.5 py-0.5 rounded-full border border-stone-200 dark:border-white/10 hover:border-blue-500 hover:text-blue-600 dark:hover:text-blue-400 bg-white/40 dark:bg-white/5 transition text-left"
                        dir="ltr"
                      >
                        ${ex}
                      </button>
                    `)}
                  </div>
                </div>

                <!-- Title Must Switch Box -->
                <div className="mt-5 rounded-[16px] border border-stone-200/90 dark:border-white/15 p-4 bg-white/50 dark:bg-white/[0.04] w-full max-w-full overflow-hidden">
                  <div className="flex items-start sm:items-center justify-between gap-3 w-full">
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] font-bold flex items-center gap-2 flex-wrap">
                        <span className="break-words">${t.strictTitleLabel}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 dark:bg-amber-900/60 dark:text-amber-200 border border-amber-200 dark:border-amber-800 font-bold shrink-0">
                          ${t.strictTitlePrecisionBadge}
                        </span>
                      </div>
                      <div className="text-[11px] opacity-75 mt-1 leading-normal break-words">${t.strictTitleDesc}</div>
                    </div>

                    <label className="relative inline-flex items-center cursor-pointer shrink-0 ms-2 mt-0.5 sm:mt-0">
                      <input
                        id="require_title"
                        type="checkbox"
                        checked=${requireTitle}
                        onChange=${(e) => setRequireTitle(e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-stone-300 peer-focus:outline-none rounded-full peer dark:bg-white/20 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-stone-900 dark:peer-checked:bg-white"></div>
                    </label>
                  </div>

                  <!-- Dynamic State Explanation Box (Strictly responsive, prevents overflow on all mobile screens) -->
                  ${requireTitle ? html`
                    <div className="mt-3 w-full max-w-full text-[12px] leading-relaxed rounded-[12px] bg-emerald-500/10 border border-emerald-500/30 p-3 text-stone-800 dark:text-stone-200 block overflow-hidden transition-all" dir=${lang === "ar" ? "rtl" : "ltr"}>
                      <div className="font-bold text-emerald-700 dark:text-emerald-400 text-[12px] mb-1.5 flex items-center gap-1.5 flex-wrap w-full">
                        <span className="shrink-0">✓</span>
                        <span className="break-words">${t.strictTitleOnBadge}</span>
                      </div>
                      <div className="opacity-90 leading-relaxed text-[11.5px] sm:text-[12px] break-words block w-full">
                        ${t.strictTitleOnText}
                      </div>
                    </div>
                  ` : html`
                    <div className="mt-3 w-full max-w-full text-[12px] leading-relaxed rounded-[12px] bg-stone-100 dark:bg-black/40 border border-stone-200 dark:border-white/10 p-3 text-stone-800 dark:text-stone-200 block overflow-hidden transition-all" dir=${lang === "ar" ? "rtl" : "ltr"}>
                      <div className="font-bold text-stone-700 dark:text-stone-300 text-[12px] mb-1.5 flex items-center gap-1.5 flex-wrap w-full">
                        <span className="shrink-0">○</span>
                        <span className="break-words">${t.strictTitleOffBadge}</span>
                      </div>
                      <div className="opacity-90 leading-relaxed text-[11.5px] sm:text-[12px] break-words block w-full">
                        ${t.strictTitleOffText}
                      </div>
                    </div>
                  `}
                </div>

                <!-- Year Filter & Limit -->
                <div className="mt-5 grid grid-cols-12 gap-4">
                  <div className="col-span-12 md:col-span-8">
                    <label className="text-[12px] font-bold opacity-80 mb-1.5 block">${t.timeRangeLabel}</label>
                    <div className="flex gap-2">
                      <input
                        id="year_from"
                        value=${yearFrom}
                        onChange=${(e) => setYearFrom(e.target.value)}
                        placeholder=${t.yearFromPlaceholder}
                        className="h-[46px] w-full rounded-[12px] border border-stone-200 dark:border-white/15 bg-white/70 dark:bg-black/30 px-3 text-[14px] text-center outline-none transition"
                        dir="ltr"
                      />
                      <input
                        id="year_to"
                        value=${yearTo}
                        onChange=${(e) => setYearTo(e.target.value)}
                        placeholder=${t.yearToPlaceholder}
                        className="h-[46px] w-full rounded-[12px] border border-stone-200 dark:border-white/15 bg-white/70 dark:bg-black/30 px-3 text-[14px] text-center outline-none transition"
                        dir="ltr"
                      />
                    </div>
                    <div className="mt-2.5 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick=${() => setYearPreset("range", "2020", "2026")}
                        className="text-[11px] px-3 py-1.5 rounded-full border border-stone-200 dark:border-white/20 hover:bg-stone-900 hover:text-white dark:hover:bg-white dark:hover:text-black transition font-sans font-bold"
                      >
                        2020 - 2026
                      </button>
                      <button
                        type="button"
                        onClick=${() => setYearPreset("now")}
                        className="text-[11px] px-3 py-1.5 rounded-full border border-stone-200 dark:border-white/20 hover:bg-stone-900 hover:text-white dark:hover:bg-white dark:hover:text-black transition font-bold"
                      >
                        ${t.yearPresetNow}
                      </button>
                      <button
                        type="button"
                        onClick=${() => setYearPreset("all")}
                        className="text-[11px] px-3 py-1.5 rounded-full border border-stone-200 dark:border-white/20 hover:bg-stone-900 hover:text-white dark:hover:bg-white dark:hover:text-black transition font-bold"
                      >
                        ${t.yearPresetAll}
                      </button>
                    </div>
                  </div>

                  <div className="col-span-12 md:col-span-4">
                    <label className="text-[12px] font-bold opacity-80 mb-1.5 block">${t.maxResultsLabel}</label>
                    <select
                      id="limit"
                      value=${limit}
                      onChange=${(e) => setLimit(e.target.value)}
                      className="w-full h-[46px] rounded-[12px] border border-stone-200 dark:border-white/15 bg-white/70 dark:bg-black/30 px-3.5 text-[14px] outline-none transition cursor-pointer"
                    >
                      <option value="5" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.limit5}</option>
                      <option value="10" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.limit10}</option>
                      <option value="25" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.limit25}</option>
                      <option value="50" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.limit50}</option>
                      <option value="100" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.limit100}</option>
                      <option value="250" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.limit250}</option>
                      <option value="999999" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.limitAll}</option>
                    </select>
                  </div>
                </div>

                <!-- Database Source & Preprint -->
                <div className="mt-5 grid grid-cols-12 gap-4">
                  <div className="col-span-12 md:col-span-6">
                    <label className="text-[12px] font-bold opacity-80 mb-1.5 block">${t.dbSourcesLabel}</label>
                    <select
                      id="db_source"
                      value=${dbSource}
                      onChange=${(e) => setDbSource(e.target.value)}
                      className="w-full h-[46px] rounded-[12px] border border-stone-200 dark:border-white/15 bg-white/70 dark:bg-black/30 px-3.5 text-[14px] outline-none transition cursor-pointer"
                    >
                      <option value="all" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.limitAll} (${lang === "ar" ? "12 محركاً" : "12 Engines"})</option>
                      <option value="pubmed" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.sourcePubmed}</option>
                      <option value="elsevier" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${isLocal ? t.sourceElsevierLocal : t.sourceElsevierCloud}</option>
                      <option value="europepmc" className="bg-[#fcfaf8] dark:bg-[#1a1816]">Europe PMC</option>
                      <option value="openalex" className="bg-[#fcfaf8] dark:bg-[#1a1816]">OpenAlex</option>
                      <option value="crossref" className="bg-[#fcfaf8] dark:bg-[#1a1816]">CrossRef</option>
                      <option value="semanticscholar" className="bg-[#fcfaf8] dark:bg-[#1a1816]">Semantic Scholar</option>
                      <option value="doaj" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${lang === "ar" ? "DOAJ (وصول حر Open Access)" : "DOAJ (Directory of Open Access Journals)"}</option>
                      <option value="core" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${lang === "ar" ? "CORE (وصول حر)" : "CORE (Open Access Repositories)"}</option>
                      <option value="zenodo" className="bg-[#fcfaf8] dark:bg-[#1a1816]">Zenodo (CERN / Open Access)</option>
                      <option value="books" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${lang === "ar" ? "مكتبات الكتب (Google Books, Open Library)" : "Book Repositories (Google Books, Open Library)"}</option>
                    </select>
                  </div>

                  <div className="col-span-12 md:col-span-6">
                    <label className="text-[12px] font-bold opacity-80 mb-1.5 block">${t.preprintsLabel}</label>
                    <label className="flex items-center justify-between h-[46px] rounded-[12px] border border-stone-200 dark:border-white/15 px-3.5 cursor-pointer bg-white/70 dark:bg-black/30 hover:border-stone-400 transition">
                      <span className="text-[13px] font-medium">${t.includePreprintsText}</span>
                      <input
                        id="include_preprint"
                        type="checkbox"
                        checked=${includePreprint}
                        onChange=${(e) => setIncludePreprint(e.target.checked)}
                        className="h-4 w-4 accent-stone-900 dark:accent-white"
                      />
                    </label>
                  </div>
                </div>

                <!-- Search Scope & Document Type Filter -->
                <div className="mt-5 grid grid-cols-12 gap-4">
                  <div className="col-span-12 md:col-span-6">
                    <label className="text-[12px] font-bold opacity-80 mb-1.5 block flex items-center gap-1.5">
                      <span>📚</span>
                      <span>${t.searchScopeLabel}</span>
                    </label>
                    <select
                      id="search_scope"
                      value=${searchScope}
                      onChange=${(e) => setSearchScope(e.target.value)}
                      className="w-full h-[46px] rounded-[12px] border border-stone-200 dark:border-white/15 bg-white/70 dark:bg-black/30 px-3.5 text-[14px] outline-none transition cursor-pointer font-medium"
                    >
                      <option value="all" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.scopeAll}</option>
                      <option value="papers" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.scopePapers}</option>
                      <option value="books" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.scopeBooks}</option>
                    </select>
                  </div>

                  <div className="col-span-12 md:col-span-6">
                    <label className="text-[12px] font-bold opacity-80 mb-1.5 block flex items-center gap-1.5">
                      <span>🔍</span>
                      <span>${t.docTypeLabel}</span>
                    </label>
                    <select
                      id="doc_type_filter"
                      value=${docTypeFilter}
                      onChange=${(e) => setDocTypeFilter(e.target.value)}
                      className="w-full h-[46px] rounded-[12px] border border-stone-200 dark:border-white/15 bg-white/70 dark:bg-black/30 px-3.5 text-[14px] outline-none transition cursor-pointer font-medium"
                    >
                      <option value="all" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.docTypeAll}</option>
                      <option value="review" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.docTypeReview}</option>
                      <option value="meta_analysis" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.docTypeMetaAnalysis}</option>
                      <option value="research" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.docTypeResearch}</option>
                      <option value="book" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.docTypeBook}</option>
                      <option value="conference" className="bg-[#fcfaf8] dark:bg-[#1a1816]">${t.docTypeConference}</option>
                    </select>
                  </div>
                </div>

                <!-- Affiliation -->
                <div className="mt-5">
                  <label className="text-[12px] font-bold opacity-80 mb-1.5 block">${t.affiliationLabel}</label>
                  <input
                    id="affiliation"
                    value=${affiliation}
                    onChange=${(e) => setAffiliation(e.target.value)}
                    placeholder=${t.affiliationPlaceholder}
                    className="w-full h-[46px] rounded-[12px] border border-stone-200 dark:border-white/15 bg-white/70 dark:bg-black/30 px-3.5 text-[14px] outline-none focus:border-stone-900 dark:focus:border-white transition"
                    dir="ltr"
                  />
                </div>

                <!-- Include Abstracts / Summaries Toggle & Quota Notice -->
                <div className="mt-5 rounded-[16px] border border-blue-300/80 dark:border-blue-700/60 p-4 bg-blue-50/50 dark:bg-blue-950/20 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-[13px] font-bold flex items-center gap-2 flex-wrap text-stone-900 dark:text-stone-100">
                        <span className="text-base">📑</span>
                        <span>${lang === "ar" ? "طلب الأبحاث مع الملخص الشامل" : "Request Papers With Full Abstracts"}</span>
                        <span className=${`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                          quota.isVip
                            ? "bg-amber-100 text-amber-800 dark:bg-amber-900/80 dark:text-amber-200 border border-amber-300 dark:border-amber-700"
                            : includeAbstracts
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/80 dark:text-emerald-200 border border-emerald-300 dark:border-emerald-700"
                              : "bg-stone-200/80 text-stone-700 dark:bg-stone-800 dark:text-stone-300 border border-stone-300 dark:border-stone-700"
                        }`}>
                          ${quota.isVip
                            ? (lang === "ar" ? "✨ VIP غير محدود" : "✨ VIP Unlimited")
                            : includeAbstracts
                              ? (lang === "ar" ? `⚡ استهلاك مضاعف (سعة ${Math.floor(quota.limit / 2)} ملخص)` : `⚡ 2x Rate (${Math.floor(quota.limit / 2)} Abstracts)`)
                              : (lang === "ar" ? `⚡ نقطة واحدة (سعة ${quota.limit} بحث)` : `⚡ 1 Credit (${quota.limit} Standard)`)}
                        </span>
                      </div>
                      <div className="text-[11px] opacity-75 mt-1 text-stone-600 dark:text-stone-300 leading-relaxed">
                        ${lang === "ar"
                          ? "تضمين الملخصات الكاملة (Abstracts) داخل قائمة النتائج وملفات التقرير الأكاديمي. عند الإيقاف: استخراج قياسي سريع للعناوين وروابط DOI."
                          : "Includes full abstracts in results and PDF dossiers. When off: fast standard search for titles and direct DOI links."}
                      </div>
                    </div>

                    <label className="relative inline-flex items-center cursor-pointer shrink-0 ms-3">
                      <input
                        id="include_abstracts"
                        type="checkbox"
                        checked=${includeAbstracts}
                        onChange=${(e) => setIncludeAbstracts(e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-stone-300 peer-focus:outline-none rounded-full peer dark:bg-white/20 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600 dark:peer-checked:bg-blue-500"></div>
                    </label>
                  </div>

                  <!-- Status badge & quota details -->
                  <div className="mt-3 pt-2.5 border-t border-blue-200/70 dark:border-blue-800/40">
                    ${quota.isVip ? html`
                      <div className="text-[11.5px] font-bold text-amber-700 dark:text-amber-400 flex items-center gap-1.5 flex-wrap">
                        <span>✨</span>
                        <span>${lang === "ar" ? "حساب VIP نشط: استخراج شامل وغير محدود للأبحاث والملخصات بدون قيود وبدون استهلاك للرصيد." : "Active VIP: Unlimited extraction of papers and abstracts without quota limits."}</span>
                      </div>
                    ` : includeAbstracts ? html`
                      <div className="rounded-[12px] border border-blue-300 dark:border-blue-800/80 bg-blue-100/70 dark:bg-blue-950/50 p-3 text-[12px] leading-relaxed text-blue-950 dark:text-blue-200">
                        <div className="font-bold flex items-center gap-1.5 mb-1 text-blue-900 dark:text-blue-100">
                          <span>ℹ️</span>
                          <span>${lang === "ar" ? "طلب الأبحاث مع الملخصات مفعل:" : "Abstracts Mode Active:"}</span>
                        </div>
                        <p className="text-[11.5px] opacity-90">
                          ${lang === "ar"
                            ? "يتم استرجاع الملخص الدراسي الكامل لكل بحث، ويستهلك هذا الطلب نقطتين (2) من رصيدك اليومي (استهلاك مضاعف x2 لكل بحث)."
                            : "Full abstracts are extracted for each study, consuming 2 credits per paper (2x rate)."}
                        </p>
                        <div className="mt-2 pt-2 border-t border-blue-200/80 dark:border-blue-800/60 text-[11px] font-bold text-blue-900 dark:text-blue-200 flex items-center justify-between flex-wrap gap-2">
                          <span>📚 ${lang === "ar" ? "توثيق شامل مدعم بالملخصات" : "Full Abstract Dossier"}</span>
                          <span className="font-mono text-[11px] text-blue-950 dark:text-blue-100 font-extrabold">
                            ${lang === "ar"
                              ? `المتبقي مع الملخصات: ${quota.remainingSummary !== undefined ? quota.remainingSummary : Math.floor(quota.remaining / 2)} من أصل ${Math.floor(quota.limit / 2)} بحث`
                              : `Remaining with abstracts: ${quota.remainingSummary !== undefined ? quota.remainingSummary : Math.floor(quota.remaining / 2)} of ${Math.floor(quota.limit / 2)}`}
                          </span>
                        </div>
                      </div>
                    ` : html`
                      <div className="text-[11.5px] text-stone-600 dark:text-stone-400 flex items-center justify-between flex-wrap gap-2">
                        <span className="flex items-center gap-1.5">
                          <span>○</span>
                          <span>${lang === "ar" ? `البحث السريع مفعل: يستهلك نقطة واحدة لكل بحث (سعة ${quota.limit} بحث).` : `Standard fast search: 1 credit per search (${quota.limit} capacity).`}</span>
                        </span>
                        <span className="font-mono font-bold text-stone-700 dark:text-stone-300">
                          ${lang === "ar" ? `الرصيد المتبقي: ${quota.remaining} من أصل ${quota.limit} بحث` : `Remaining: ${quota.remaining} of ${quota.limit}`}
                        </span>
                      </div>
                    `}
                  </div>
                </div>

                <!-- Submit Button -->
                <div className="mt-8 flex gap-3">
                  <button
                    id="submit-btn"
                    type="submit"
                    disabled=${isSearching}
                    className="flex-1 h-[52px] rounded-[16px] bg-[#0c0a09] dark:bg-white text-white dark:text-black font-black text-[15px] hover:opacity-90 disabled:opacity-50 transition flex items-center justify-center gap-2 shadow-md cursor-pointer"
                  >
                    ${isSearching ? html`
                      <span className="flex items-center gap-2">
                        <span className="animate-spin text-lg">◌</span> ${lang === "ar" ? "جاري المعالجة والمسح المتوازي..." : "Processing & Parallel Searching..."}
                      </span>
                    ` : html`
                      <span>${lang === "ar" ? "إطلاق البحث الذكي المتوازي ↗ (Ctrl + Enter)" : "Launch Smart Parallel Search ↗ (Ctrl + Enter)"}</span>
                    `}
                  </button>
                </div>

                <!-- Loading Panel -->
                ${isSearching ? html`
                  <div className="mt-6 rounded-[18px] border border-amber-200 dark:border-amber-900/50 bg-amber-50/90 dark:bg-amber-950/50 p-5 shadow-sm glass-panel animate-fade-in">
                    <div className="flex items-center justify-between mb-3">
                      <div className="text-[14px] font-bold text-amber-900 dark:text-amber-200 flex items-center gap-2">
                        <span className="animate-pulse text-amber-600">●</span> ${localizeTaskMessage(statusMsg, lang)}
                      </div>
                      <button
                        type="button"
                        onClick=${handleCancelTask}
                        className="text-[12px] font-bold px-3 py-1 rounded-full bg-white border border-rose-300 text-rose-700 dark:bg-rose-950/40 dark:border-rose-900 dark:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-900/30 transition shadow-sm cursor-pointer flex items-center gap-1.5"
                        title=${lang === "ar" ? "إيقاف عملية البحث الجارية فوراً" : "Stop ongoing search immediately"}
                      >
                        <span className="text-[13px] font-black">✕</span> ${lang === "ar" ? "إيقاف البحث" : "Stop Search"}
                      </button>
                    </div>

                    <div className="h-2.5 w-full rounded-full bg-amber-200/60 dark:bg-amber-900/30 overflow-hidden">
                      <div
                        className="h-full bg-amber-500 rounded-full transition-all duration-500"
                        style=${{ width: `${progress}%` }}
                      />
                    </div>

                    <div className="mt-2.5 flex justify-between text-[11px] opacity-80 font-sans font-bold">
                      <span>${progress}% ${lang === "ar" ? "مكتمل" : "completed"}</span>
                      <span>Task ID: ${taskId}</span>
                    </div>
                  </div>
                ` : null}

                <!-- Download Ready Panel -->
                ${showDownloadPanel ? html`
                  <div className="mt-6 rounded-[18px] border border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/90 dark:bg-emerald-950/50 p-5 shadow-sm glass-panel space-y-4 animate-fade-in">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="text-[14px] font-bold text-emerald-900 dark:text-emerald-200 flex items-center gap-2">
                        <span className="text-emerald-600 dark:text-emerald-400 font-black">✓</span> ${doneTitle}
                      </div>
                      ${counts ? html`
                        <span className="text-[11px] px-2.5 py-1 rounded-full bg-emerald-200/60 dark:bg-emerald-900/40 text-emerald-900 dark:text-emerald-200 font-bold">
                          ${lang === "ar" ? `محكّم: ${counts.peer} • مسودات: ${counts.preprints} • دفعات: ${counts.batches}` : `Peer-Reviewed: ${counts.peer} • Preprints: ${counts.preprints} • Batches: ${counts.batches}`}
                        </span>
                      ` : null}
                    </div>

                    <!-- Local Save Path Display (For Local Package) -->
                    ${isLocal && savePath ? html`
                      <div className="rounded-[14px] border border-emerald-300 dark:border-emerald-800 bg-white/80 dark:bg-black/40 p-3.5 space-y-2 text-right">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[12px] font-bold text-stone-700 dark:text-stone-300 flex items-center gap-1.5">
                            ${lang === "ar" ? "📁 مسار حفظ الحزمة على جهازك:" : "📁 Local Package Save Path:"}
                          </span>
                          <button
                            type="button"
                            onClick=${() => copyToClipboard(savePath, () => {
                              setCopiedPath(true);
                              setTimeout(() => setCopiedPath(false), 3000);
                            })}
                            className="text-[11px] px-3 py-1 rounded-lg bg-stone-900 text-white dark:bg-white dark:text-black font-bold hover:opacity-85 transition flex items-center gap-1 shadow-sm cursor-pointer"
                          >
                            ${copiedPath ? (lang === "ar" ? "✓ تم نسخ المسار!" : "✓ Path Copied!") : (lang === "ar" ? "📋 نسخ المسار" : "📋 Copy Path")}
                          </button>
                        </div>
                        <div className="text-[12px] font-mono select-all break-all bg-stone-100 dark:bg-white/5 p-2.5 rounded-lg border border-stone-200 dark:border-white/10 text-stone-900 dark:text-stone-100 text-left" dir="ltr">
                          ${savePath}
                        </div>
                        <p className="text-[11px] text-stone-500 dark:text-stone-400">
                          ${lang === "ar" ? "تم حفظ ملف الـ ZIP المضغوط مباشرة في المسار الموضح أعلاه، وتم حذف ملفات PDF الفردية وملف التكست لتوفير المساحة." : "The compressed ZIP archive has been saved directly to the path above. Temporary individual files were cleaned up to conserve storage."}
                        </p>
                      </div>
                    ` : null}

                    <div className="flex flex-wrap items-center gap-3 pt-1">
                      <a
                        href=${downloadUrl}
                        download=${filename || (fileType === "pdf" ? "Academic_Report.pdf" : "Academic_Archive.zip")}
                        className="inline-flex h-[44px] px-5 rounded-[12px] bg-emerald-600 hover:bg-emerald-700 text-white text-[13px] font-black items-center gap-2 transition shadow-sm cursor-pointer"
                        title=${lang === "ar" ? "تحميل وتنزيل الملف مباشرة إلى جهازك" : "Download and save file directly to your device"}
                      >
                        <span>📥</span> ${lang === "ar" ? (fileType === "pdf" ? "تحميل التقرير (PDF)" : "تحميل الحزمة (ZIP)") : (fileType === "pdf" ? "Download Report (PDF)" : "Download Archive (ZIP)")}
                      </a>
                      ${isLocal && savePath ? html`
                        <button
                          type="button"
                          onClick=${() => copyToClipboard(savePath, () => {
                            setCopiedPath(true);
                            setTimeout(() => setCopiedPath(false), 3000);
                          })}
                          className="inline-flex h-[44px] px-4 rounded-[12px] border border-emerald-600 text-emerald-800 dark:text-emerald-200 text-[13px] font-bold items-center gap-1.5 hover:bg-emerald-100/50 transition cursor-pointer"
                        >
                          ${copiedPath ? (lang === "ar" ? "✓ تم النسخ" : "✓ Copied") : (lang === "ar" ? "📋 نسخ مسار الحفظ" : "📋 Copy Save Path")}
                        </button>
                      ` : null}
                    </div>
                  </div>
                ` : null}
              </div>
            </form>

            <!-- Live Interactive Results Browser -->
            ${resultsPapers && resultsPapers.length > 0 ? html`
              <div ref=${resultsSectionRef} className="mt-8 space-y-4 animate-fade-in">
                <div className=${`rounded-[24px] border ${isDark ? "bg-[#141210]/85 border-white/10" : "bg-white/90 border-stone-200/90"} glass-panel shadow-[0_12px_40px_rgba(0,0,0,0.12)] p-6 md:p-8`}>
                  <!-- Results Header -->
                  <div className="flex items-center justify-between flex-wrap gap-3 pb-5 border-b border-stone-200/70 dark:border-white/10">
                    <div>
                      <h3 className="text-[18px] font-black flex items-center gap-2">
                        <span>📚 ${lang === "ar" ? "مستعرض الأوراق البحثية المستخرجة" : "Retrieved Papers Explorer"}</span>
                        <span className="text-[12px] px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/60 dark:text-blue-200 font-bold font-sans">
                          ${filteredPapers.length} / ${resultsPapers.length}
                        </span>
                      </h3>
                      <p className="text-[12px] opacity-70 mt-1">
                        ${includeAbstracts ? (lang === "ar" ? "يمكنك قراءة الملخصات، فتح الروابط مباشرة، ونسخ الاقتباسات (APA / BibTeX) بنقرة زر" : "Read abstracts, open direct links, and copy citations (APA / BibTeX) with a single click.") : (lang === "ar" ? "استعراض بيانات الأوراق وفحص الروابط المباشرة ونسخ الاقتباسات (APA / BibTeX)" : "Explore paper metadata, open direct links, and copy citations (APA / BibTeX).")}
                      </p>
                    </div>

                    <!-- Filter Tabs -->
                    <div className="flex items-center gap-1 bg-stone-100 dark:bg-white/5 p-1 rounded-[14px] text-[12px] font-bold">
                      <button
                        type="button"
                        onClick=${() => setPaperFilter("all")}
                        className=${`px-3 py-1.5 rounded-[10px] transition ${paperFilter === "all" ? "bg-white dark:bg-stone-800 text-stone-900 dark:text-white shadow-sm" : "opacity-70 hover:opacity-100"}`}
                      >
                        ${lang === "ar" ? "الكل" : "All"} (${resultsPapers.length})
                      </button>
                      <button
                        type="button"
                        onClick=${() => setPaperFilter("peer")}
                        className=${`px-3 py-1.5 rounded-[10px] transition ${paperFilter === "peer" ? "bg-white dark:bg-stone-800 text-emerald-600 dark:text-emerald-400 shadow-sm" : "opacity-70 hover:opacity-100"}`}
                      >
                        ${lang === "ar" ? "محكّمة" : "Peer-Reviewed"} (${resultsPapers.filter(p => !p.is_preprint).length})
                      </button>
                      <button
                        type="button"
                        onClick=${() => setPaperFilter("preprints")}
                        className=${`px-3 py-1.5 rounded-[10px] transition ${paperFilter === "preprints" ? "bg-white dark:bg-stone-800 text-amber-600 dark:text-amber-400 shadow-sm" : "opacity-70 hover:opacity-100"}`}
                      >
                        ${t.filterPreprints} (${resultsPapers.filter(p => p.is_preprint).length})
                      </button>
                      <button
                        type="button"
                        onClick=${() => setPaperFilter("oa")}
                        className=${`px-3 py-1.5 rounded-[10px] transition ${paperFilter === "oa" ? "bg-white dark:bg-stone-800 text-blue-600 dark:text-blue-400 shadow-sm" : "opacity-70 hover:opacity-100"}`}
                      >
                        ${lang === "ar" ? "وصول حر OA" : "Open Access (OA)"} (${resultsPapers.filter(p => p.is_oa || p.oa_url || p.pdf_url).length})
                      </button>
                      <button
                        type="button"
                        onClick=${() => setPaperFilter("review")}
                        className=${`px-3 py-1.5 rounded-[10px] transition ${paperFilter === "review" ? "bg-white dark:bg-stone-800 text-purple-600 dark:text-purple-400 shadow-sm" : "opacity-70 hover:opacity-100"}`}
                      >
                        ${t.filterReviews} (${resultsPapers.filter(p => p.doc_type === "review" || p.doc_type === "meta_analysis" || p.doc_partition === "review").length})
                      </button>
                      <button
                        type="button"
                        onClick=${() => setPaperFilter("book")}
                        className=${`px-3 py-1.5 rounded-[10px] transition ${paperFilter === "book" ? "bg-white dark:bg-stone-800 text-amber-600 dark:text-amber-400 shadow-sm" : "opacity-70 hover:opacity-100"}`}
                      >
                        ${t.filterBooks} (${resultsPapers.filter(p => p.doc_type === "book" || p.doc_partition === "book").length})
                      </button>
                      <button
                        type="button"
                        onClick=${() => setPaperFilter("research")}
                        className=${`px-3 py-1.5 rounded-[10px] transition ${paperFilter === "research" ? "bg-white dark:bg-stone-800 text-teal-600 dark:text-teal-400 shadow-sm" : "opacity-70 hover:opacity-100"}`}
                      >
                        ${t.filterResearch} (${resultsPapers.filter(p => p.doc_type === "research" || p.doc_partition === "research").length})
                      </button>
                    </div>
                  </div>

                  <!-- Filter search box in results -->
                  <div className="pt-4 pb-2">
                    <input
                      type="text"
                      value=${resultsQuery}
                      onChange=${(e) => setResultsQuery(e.target.value)}
                      placeholder=${lang === "ar" ? "بحث وتصفية سريعة داخل النتائج (بالعنوان، المؤلف، أو المجلة)..." : "Filter results (by title, author, or journal)..."}
                      className="w-full h-[42px] rounded-[12px] border border-stone-200 dark:border-white/10 bg-white/60 dark:bg-black/30 px-3.5 text-[13px] outline-none focus:border-stone-900 dark:focus:border-white transition"
                    />
                  </div>

                  <!-- Cards List -->
                  <div className="mt-4 space-y-4 max-h-[700px] overflow-y-auto pr-1">
                    ${filteredPapers.length === 0 ? html`
                      <div className="py-12 text-center opacity-60 text-[14px]">
                        ${lang === "ar" ? "لا توجد نتائج تطابق معايير التصفية المحددة." : "No results match the specified filter criteria."}
                      </div>
                    ` : filteredPapers.map((paper, idx) => {
                      const isExpanded = !!expandedAbstracts[idx];
                      const isPreprint = !!paper.is_preprint;
                      const hasOA = !!(paper.is_oa || paper.oa_url || paper.pdf_url);
                      const oaLink = paper.oa_url || paper.pdf_url || (paper.doi ? `https://doi.org/${paper.doi}` : null);
                      const authorsStr = (paper.authors && paper.authors.length) ? paper.authors.join(", ") : "Unknown Authors";

                      return html`
                        <div
                          key=${idx}
                          className=${`paper-card rounded-[18px] border p-5 transition-all ${
                            isDark
                              ? "bg-stone-900/60 border-white/10 hover:border-white/20"
                              : "bg-white/80 border-stone-200/80 hover:border-stone-300"
                          } shadow-sm space-y-3`}
                        >
                          <!-- Top Badges -->
                          <div className="flex items-center justify-between flex-wrap gap-2">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className=${`text-[11px] px-2.5 py-0.5 rounded-full font-bold border ${
                                isPreprint
                                  ? "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-300 dark:border-amber-800"
                                  : "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800"
                              }`}>
                                ${isPreprint ? t.preprint : t.peerReviewed}
                              </span>

                              ${paper.doc_type && paper.doc_type !== "unknown" ? html`
                                <span className=${`text-[10px] px-2.5 py-0.5 rounded-full font-bold border ${
                                  paper.doc_type === "review"
                                    ? "bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300 border-purple-300 dark:border-purple-800"
                                    : paper.doc_type === "meta_analysis"
                                      ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300 border-indigo-300 dark:border-indigo-800"
                                      : paper.doc_type === "book"
                                        ? "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-300 dark:border-amber-800"
                                        : paper.doc_type === "conference"
                                          ? "bg-teal-100 text-teal-800 dark:bg-teal-950/60 dark:text-teal-300 border-teal-300 dark:border-teal-800"
                                          : "bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 border-blue-200 dark:border-blue-800"
                                }`}>
                                  ${paper.doc_type === "review" ? t.badgeReview :
                                    paper.doc_type === "meta_analysis" ? t.badgeMetaAnalysis :
                                    paper.doc_type === "book" ? t.badgeBook :
                                    paper.doc_type === "conference" ? t.badgeConference :
                                    t.badgeResearch}
                                </span>
                              ` : null}

                              ${paper.year && paper.year !== "0000" ? html`
                                <span className="text-[11px] px-2 py-0.5 rounded-full bg-stone-100 dark:bg-white/10 font-sans font-bold opacity-80">
                                  ${paper.year}
                                </span>
                              ` : null}

                              ${hasOA ? html`
                                <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 font-bold border border-blue-200 dark:border-blue-800 flex items-center gap-1">
                                  <span>🔓</span> Open Access
                                </span>
                              ` : null}

                              ${paper.citation_count > 0 ? html`
                                <span className="text-[11px] px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300 font-sans font-bold">
                                  ★ ${paper.citation_count} ${t.citationsCount}
                                </span>
                              ` : null}
                            </div>

                            <div className="text-[11px] opacity-60 font-mono">
                              ${(paper.sources || []).join(" · ")}
                            </div>
                          </div>

                          <!-- Paper Title -->
                          <h4 className="text-[15px] font-black leading-snug text-stone-950 dark:text-stone-50" dir="ltr">
                            ${oaLink ? html`
                              <a href=${oaLink} target="_blank" rel="noopener noreferrer" className="hover:text-blue-600 dark:hover:text-blue-400 hover:underline transition">
                                ${paper.title || "No Title"}
                              </a>
                            ` : (paper.title || "No Title")}
                          </h4>

                          <!-- Authors & Venue -->
                          <div className="text-[12px] opacity-75 space-y-1" dir="ltr">
                            <div className="font-semibold text-stone-700 dark:text-stone-300 truncate" title=${authorsStr}>
                              👤 ${authorsStr}
                            </div>
                            ${paper.journal ? html`
                              <div className="italic text-stone-600 dark:text-stone-400">
                                📖 ${paper.journal}
                              </div>
                            ` : null}
                            ${paper.publisher && paper.publisher !== paper.journal ? html`
                              <div className="text-[11.5px] text-stone-500 dark:text-stone-400 font-medium flex items-center gap-1.5">
                                <span>🏛️</span>
                                <span>${paper.publisher}</span>
                              </div>
                            ` : null}
                          </div>

                          <!-- Abstract section: rendered strictly ONLY when includeAbstracts is TRUE -->
                          ${includeAbstracts ? (
                            (paper.abstract && paper.abstract.trim() && paper.abstract !== "No abstract provided in source metadata.") ? html`
                              <div className="pt-1">
                                <p className=${`text-[12px] leading-relaxed text-stone-700 dark:text-stone-300 ${!isExpanded ? "line-clamp-2" : ""}`} dir="ltr">
                                  ${paper.abstract}
                                </p>
                                <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                                  <button
                                    type="button"
                                    onClick=${() => toggleAbstract(idx)}
                                    className="text-[11px] font-bold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
                                  >
                                    ${isExpanded ? (lang === "ar" ? "طي الملخص ▴" : "Collapse Abstract ▴") : (lang === "ar" ? "قراءة الملخص هنا ▾" : "Read Abstract Here ▾")}
                                  </button>
                                  <button
                                    type="button"
                                    onClick=${() => {
                                      setAbstractModalPaper(paper);
                                      setShowAbstractModal(true);
                                    }}
                                    className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-800/50 border border-blue-200 dark:border-blue-700/50 flex items-center gap-1 transition cursor-pointer"
                                  >
                                    <span>📑</span> ${lang === "ar" ? "عرض في نافذة الملخص (Abstract)" : "View in Abstract Window"}
                                  </button>
                                </div>
                              </div>
                            ` : html`
                              <div className="pt-1 flex items-center justify-between flex-wrap gap-2">
                                <div className="text-[11px] opacity-50 italic">
                                  [${lang === "ar" ? "الملخص غير متوفر في البيانات الوصفية للمصدر" : "Abstract not available in source metadata"}]
                                </div>
                              </div>
                            `
                          ) : null}

                          <!-- Bottom Actions -->
                          <div className="pt-2 flex items-center justify-between flex-wrap gap-2 border-t border-stone-200/50 dark:border-white/5 text-[11px]">
                            <div className="flex items-center gap-3">
                              ${paper.doi ? html`
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <a
                                    href=${`https://doi.org/${paper.doi}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-600 dark:text-blue-400 font-mono font-bold hover:underline flex items-center gap-1"
                                    dir="ltr"
                                  >
                                    <span>🔗 DOI:</span> ${paper.doi}
                                  </a>
                                  <button
                                    type="button"
                                    onClick=${() => {
                                      copyToClipboard(`https://doi.org/${paper.doi}`, () => {
                                        setCopiedDoiUrlId(idx);
                                        setTimeout(() => setCopiedDoiUrlId(null), 2000);
                                      });
                                    }}
                                    className=${`text-[11px] px-2 py-0.5 rounded-[6px] font-bold transition flex items-center gap-1 ${
                                      copiedDoiUrlId === idx
                                        ? "bg-emerald-600 text-white"
                                        : "bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800/60 hover:bg-blue-100 dark:hover:bg-blue-900/60"
                                    }`}
                                    title=${lang === "ar" ? "نسخ رابط DOI بصورة رابط كامل (https://doi.org/...)" : "Copy full DOI link (https://doi.org/...)"}
                                  >
                                    <span>${copiedDoiUrlId === idx ? t.copyDoiLinkDone : t.copyDoiLinkBtn}</span>
                                  </button>
                                </div>
                              ` : null}

                              ${oaLink ? html`
                                <a
                                  href=${oaLink}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-emerald-600 dark:text-emerald-400 font-bold hover:underline flex items-center gap-1"
                                >
                                  <span>${t.directLinkDownload}</span>
                                </a>
                              ` : (paper.doi ? html`
                                ${(() => {
                                  const acc = cardAccessMap[paper.doi];
                                  const isChecking = cardCheckingMap[paper.doi];
                                  if (isChecking) {
                                    return html`
                                      <span className="text-[11px] text-stone-500 dark:text-stone-400 font-medium flex items-center gap-1">
                                        <span className="animate-spin inline-block">⏳</span>
                                        <span>${t.checkingAvailability}</span>
                                      </span>
                                    `;
                                  }
                                   if (acc) {
                                     if (acc.is_oa && acc.oa_url) {
                                       return html`
                                         <a
                                           href=${acc.oa_url}
                                           target="_blank"
                                           rel="noopener noreferrer"
                                           className="text-emerald-600 dark:text-emerald-400 font-bold hover:underline flex items-center gap-1 text-[11px]"
                                           title=${lang === "ar" ? "تم العثور على نسخة مفتوحة عبر Unpaywall" : "Open Access copy found via Unpaywall"}
                                         >
                                           <span>${t.freeOaDownload}</span>
                                         </a>
                                       `;
                                     }
                                     return html`
                                       <span className="text-[11px] text-stone-400 dark:text-stone-500 font-medium" title=${lang === "ar" ? "غير متوفر في الوصول المفتوح عبر Unpaywall" : "Not available via Unpaywall Open Access"}>
                                         ${t.publisherSubscription}
                                       </span>
                                     `;
                                   }
                                   return html`
                                     <button
                                       type="button"
                                       onClick=${() => handleCheckCardAccess(paper.doi, paper.title)}
                                       className="text-[11px] px-2 py-0.5 rounded-[6px] font-bold bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30 hover:bg-amber-500/20 transition flex items-center gap-1 cursor-pointer"
                                       title=${lang === "ar" ? "التحقق من توفر نسخة مجانية عبر Unpaywall أو Sci-Hub أو ResearchGate" : "Check free access via Unpaywall, Sci-Hub, or ResearchGate"}
                                     >
                                       <span>${t.checkFreeAccessBtn}</span>
                                     </button>
                                   `;
                                 })()}
                               ` : null)}

                               <!-- Permanent Sci-Hub Button on Card -->
                               ${(paper.doi || paper.title) ? (() => {
                                 const acc = cardAccessMap[paper.doi];
                                 const shConfirmed = acc?.has_scihub && acc?.scihub_url;
                                 const shUrl = acc?.scihub_url || `https://sci-hub.ren/${encodeURIComponent(paper.doi || paper.title)}`;
                                 return html`
                                   <a
                                     href=${shUrl}
                                     target="_blank"
                                     rel="noopener noreferrer"
                                     className="text-amber-600 dark:text-amber-400 font-bold hover:underline flex items-center gap-1 text-[11px]"
                                     title=${shConfirmed ? (lang === "ar" ? "نسخة متوفرة ومؤكدة عبر مستودع بديل (Sci-Hub)" : "Confirmed available on Sci-Hub") : (lang === "ar" ? "البحث في مستودع Sci-Hub" : "Search in Sci-Hub repository")}
                                   >
                                     <span>🔓 Sci-Hub</span>
                                     ${shConfirmed ? html`
                                       <span className="text-[10px] bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-200 border border-amber-300 dark:border-amber-700 px-1 rounded font-bold">
                                         ${t.badgeAvailable}
                                       </span>
                                     ` : null}
                                   </a>
                                 `;
                               })() : null}

                              <!-- ResearchGate Button on Card -->
                              ${(() => {
                                const acc = cardAccessMap[paper.doi];
                                const rg = acc?.researchgate || {};
                                const rgUrl = rg.download_url || rg.url || `https://www.researchgate.net/search/publication?q=${encodeURIComponent(paper.doi || paper.title)}`;
                                const hasDl = rg.has_download;
                                return html`
                                  <a
                                    href=${rgUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-teal-600 dark:text-teal-400 font-bold hover:underline flex items-center gap-1 text-[11px]"
                                    title=${hasDl ? (lang === "ar" ? "نسخة كاملة متاحة للتنزيل عبر ResearchGate" : "Full paper available for download via ResearchGate") : (lang === "ar" ? "البحث والتحقق من توفر البحث على ResearchGate" : "Search & verify publication on ResearchGate")}
                                  >
                                    <span>🔬 ResearchGate</span>
                                    ${hasDl ? html`
                                      <span className="text-[10px] bg-teal-100 dark:bg-teal-950 text-teal-800 dark:text-teal-200 border border-teal-300 dark:border-teal-700 px-1 rounded font-bold">
                                        ${t.badgeDownload}
                                      </span>
                                    ` : null}
                                  </a>
                                `;
                              })()}
                            </div>

                            

                            <!-- Citation Buttons (APA 7th & BibTeX) -->
                            <div className="flex items-center gap-1.5">
                              <button
                                type="button"
                                onClick=${() => handleCopyCitation(paper, idx, "apa")}
                                className="h-[28px] px-2.5 rounded-[8px] border border-stone-200 dark:border-white/10 hover:bg-stone-100 dark:hover:bg-white/10 transition font-bold text-[10px] cursor-pointer"
                                title=${lang === "ar" ? "نسخ توثيق APA 7th" : "Copy APA 7th"}
                              >
                                ${copiedCiteId === `${idx}_apa` ? (lang === "ar" ? "✓ تم نسخ APA" : "✓ Copied APA") : "📋 APA"}
                              </button>
                              <button
                                type="button"
                                onClick=${() => handleCopyCitation(paper, idx, "bibtex")}
                                className="h-[28px] px-2.5 rounded-[8px] border border-stone-200 dark:border-white/10 hover:bg-stone-100 dark:hover:bg-white/10 transition font-bold font-mono text-[10px] cursor-pointer"
                                title=${lang === "ar" ? "نسخ كود BibTeX" : "Copy BibTeX code"}
                              >
                                ${copiedCiteId === `${idx}_bibtex` ? (lang === "ar" ? "✓ تم نسخ BibTeX" : "✓ Copied BibTeX") : "📋 BibTeX"}
                              </button>
                            </div>
                          </div>
                        </div>
                      `;
                    })}
                  </div>
                </div>
              </div>
            ` : null}
          </section>

          <!-- History Aside -->
          <aside className="col-span-12 lg:col-span-4 order-last lg:order-none">
            <div className=${`rounded-[20px] sm:rounded-[24px] border ${isDark ? "bg-[#141210]/85 border-white/10" : "bg-white/90 border-stone-200/90"} glass-panel shadow-[0_12px_40px_rgba(0,0,0,0.12)] p-4 sm:p-6 lg:sticky lg:top-[88px]`}>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-[16px] font-black">${isLocal ? (lang === "ar" ? "سجل الحزم المستخرجة محلياً" : "Locally Extracted Packages") : (lang === "ar" ? "سجل الحزم المستخرجة" : "Extracted Packages History")}</h3>
                  <p className="text-[11px] opacity-70 mt-0.5">${isLocal ? (lang === "ar" ? "الحزم المحفوظة على حاسوبك الشخصي" : "Packages saved on your PC") : (lang === "ar" ? "الحزم المحفوظة على الخادم (48 ساعة)" : "Packages saved on server (48 hours)")}</p>
                </div>
                <button
                  type="button"
                  onClick=${() => loadHistory(false)}
                  disabled=${loadingHistory}
                  className="text-[12px] px-3.5 py-1.5 rounded-full bg-stone-900 text-white dark:bg-white dark:text-black font-bold hover:opacity-90 transition disabled:opacity-50 shadow-sm cursor-pointer"
                >
                  ${loadingHistory ? (lang === "ar" ? "جاري..." : "Loading...") : (lang === "ar" ? "تحديث ◫" : "Refresh ◫")}
                </button>
              </div>

              <div className="overflow-auto max-h-[480px] rounded-[16px] border border-stone-100 dark:border-white/10 bg-white/50 dark:bg-black/30">
                <table className="w-full text-[12px]">
                  <thead className="bg-stone-50/80 dark:bg-white/5 text-[11px] opacity-70 sticky top-0">
                    <tr>
                      <th className=${`p-3 font-bold ${lang === "ar" ? "text-right" : "text-left"}`}>${lang === "ar" ? "عملية البحث والملف" : "Search Query & File"}</th>
                      <th className=${`p-3 font-bold ${lang === "ar" ? "text-right" : "text-left"}`}>${lang === "ar" ? "الحجم" : "Size"}</th>
                      <th className="text-center p-3 font-bold">${lang === "ar" ? "الإجراءات" : "Actions"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${historyList.length === 0 ? html`
                      <tr>
                        <td colSpan=${3} className="p-6 text-center opacity-60 text-[13px]">
                          ${lang === "ar" ? html`لا توجد عمليات بحث سابقة معروضة.<br />اضغط <b>تحديث ◫</b> لقراءة الحزم المحفوظة في المجلد` : html`No previous searches displayed.<br />Click <b>Refresh ◫</b> to scan saved packages in folder`}
                        </td>
                      </tr>
                    ` : historyList.map((item, idx) => html`
                      <tr key=${idx} className="border-t border-stone-100 dark:border-white/5 hover:bg-white/40 dark:hover:bg-white/5 transition">
                        <td className="p-3">
                          <div className="font-bold text-[13px] text-blue-700 dark:text-blue-400 flex items-center gap-1">
                            <span>🔍</span> ${item.query || (lang === "ar" ? "بحث أكاديمي" : "Academic Search")}
                          </div>
                          <div className="text-[10px] opacity-60 truncate max-w-[180px] mt-0.5" title=${item.filename} dir="ltr">
                            ${item.filename}
                          </div>
                          <div className="text-[10px] opacity-40 mt-0.5">
                            ${item.timestamp || "—"}
                          </div>
                        </td>
                        <td className="p-3 opacity-80 whitespace-nowrap font-sans font-semibold text-[11px]">
                          ${item.size || "—"}
                        </td>
                        <td className="p-3 text-center">
                          <div className="flex items-center justify-center gap-1.5 flex-wrap">
                            <button
                              type="button"
                              onClick=${() => handleLoadSearch(item)}
                              className="inline-flex px-2.5 py-1 rounded-[8px] bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-bold shadow-sm transition cursor-pointer"
                              title=${lang === "ar" ? "استعراض أوراق وملخصات واستشهادات هذا البحث في الصفحة كبطاقات تفاعلية" : "Explore papers, abstracts, and citations for this search"}
                            >
                              👁️ ${lang === "ar" ? "النتائج" : "Results"}
                            </button>
                            <a
                              href=${item.download_url}
                              download=${item.filename}
                              className="inline-flex px-2.5 py-1 rounded-[8px] bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold shadow-sm transition cursor-pointer items-center gap-1"
                              title=${lang === "ar" ? "تحميل هذا الملف مباشرة إلى جهازك" : "Download file directly"}
                            >
                              <span>📥</span> ${lang === "ar" ? "تحميل" : "Download"}
                            </a>
                            <button
                              type="button"
                              onClick=${() => handleDeleteHistory(item)}
                              className="inline-flex px-2 py-1 rounded-[8px] bg-red-100 hover:bg-red-200 dark:bg-red-950/60 dark:hover:bg-red-900/80 text-red-700 dark:text-red-300 text-[11px] font-bold shadow-sm transition cursor-pointer"
                              title=${lang === "ar" ? "مسح هذا الملف نهائياً من القرص" : "Permanently delete this file from disk"}
                            >
                              🗑️ ${lang === "ar" ? "مسح" : "Delete"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    `)}
                  </tbody>
                </table>
              </div>

              <div className="mt-4 text-[11px] leading-5 opacity-70 p-3 rounded-[14px] bg-white/40 dark:bg-white/5 border border-stone-100 dark:border-white/10">
                <b>${lang === "ar" ? "ملاحظة:" : "Note:"}</b> ${lang === "ar" ? "يتم فرز الحزم زمنياً من الأحدث إلى الأقدم. سيتم مسح أي حزمة آلياً بعد مرور 48 ساعة على بنائها." : "Packages are sorted chronologically from newest to oldest. Stored packages are automatically retained locally."}
              </div>
            </div>
          </aside>
          `}
                  <!-- Comprehensive Platform User Guide (Full-Width at Page End) -->
          <div className="col-span-12 mt-6 sm:mt-8">
            <div className=${`rounded-[22px] sm:rounded-[28px] border ${isDark ? "bg-[#141210]/95 border-white/10" : "bg-white/95 border-stone-200/90"} glass-panel shadow-[0_12px_45px_rgba(0,0,0,0.08)] p-5 sm:p-8 space-y-6`}>
              
              <!-- Guide Main Header -->
              <div className="flex items-center justify-between flex-wrap gap-3 pb-5 border-b border-stone-200/70 dark:border-white/10">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-[16px] bg-blue-500/10 text-blue-600 dark:text-blue-400 grid place-items-center text-2xl shrink-0">
                    🧭
                  </div>
                  <div>
                    <h3 className="text-[17px] sm:text-[20px] font-black text-stone-900 dark:text-stone-100">
                      ${lang === "ar" ? "دليل الاستخدام الشامل وميزات منصة محيط المعرفة" : "Comprehensive User Guide & Platform Architecture"}
                    </h3>
                    <p className="text-[12px] sm:text-[13px] opacity-75 mt-0.5">
                      ${lang === "ar" ? "شرح تفصيلي لكافة أدوات البحث والاسترجاع، الفلاتر الذكية، خيارات التقارير، وسياسة الخصوصية الأكاديمية الصارمة." : "In-depth reference for search engines, intelligent filters, citation exports, reports, and privacy policies."}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 font-bold">
                    ${lang === "ar" ? "🛡️ خصوصية مطلقة 100%" : "🛡️ 100% Zero Data Retention"}
                  </span>
                </div>
              </div>

              <!-- 1. Strict Privacy & Zero Data Retention Callout -->
              <div className="rounded-[18px] border border-emerald-500/40 bg-emerald-500/10 dark:bg-emerald-950/30 p-4 sm:p-5 text-emerald-950 dark:text-emerald-200 shadow-sm">
                <div className="flex items-center gap-2 font-black text-[13px] sm:text-[14px] text-emerald-800 dark:text-emerald-300 mb-2">
                  <span className="text-xl">🛡️</span>
                  <span>${lang === "ar" ? "ضمان الخصوصية التامة: الموقع لا يحتفظ بأي معلومات للمستخدمين إطلاقاً" : "Zero Data Retention Guarantee: 100% User Privacy"}</span>
                </div>
                <p className="text-[12px] sm:text-[13px] leading-relaxed opacity-95 text-stone-800 dark:text-stone-200">
                  ${lang === "ar"
                    ? " المنصة لا تحتفظ ولا تسجل أي معلومات أو بيانات شخصية للمستخدمين نهائياً. لا يتم تخزين استعلاماتك البحثية، ولا سجلات هويتك، ولا عناوين الـ IP، ولا نتائج البحث في أي قواعد بيانات دائمة أو ملفات تعريفية. تتم معالجة كافة الاستعلامات وتوليد التقارير مؤقتاً في الذاكرة الحية (In-Memory) خلال جلستك النشطة فقط، وتُمسح الملفات المؤقتة تلقائياً."
                    : " Knowledge Ocean does not log, track, or retain any personal user data, search queries, IP addresses, or retrieved results in any permanent database. All queries, indexing, and report generations execute strictly in volatile memory (In-Memory) during your active session and temporary files are automatically purged."
                  }
                </p>
              </div>

              <!-- 2. Detailed Cards Grid -->
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-[12px] leading-relaxed">
                
                <!-- Card 1: Search Modes -->
                <div className="rounded-[18px] border border-stone-200/80 dark:border-white/10 bg-stone-50/70 dark:bg-white/[0.03] p-4 sm:p-5 space-y-2">
                  <div className="font-black text-[13.5px] text-blue-700 dark:text-blue-400 flex items-center gap-2">
                    <span className="text-base">🔍</span>
                    <span>${lang === "ar" ? "1. محاور وطرق البحث العلمي الذكي" : "1. Smart Search Modes & Query Logic"}</span>
                  </div>
                  <p className="opacity-85 text-stone-700 dark:text-stone-300 whitespace-pre-line">
                    ${lang === "ar"
                      ? "• بحث الكلمات المفتاحية: يدعم المعاملات المنطقية (AND, OR, NOT) والأقواس لحصر العلاقات بدقة، وعلامات التنصيص («...») للبحث عن عبارات مركبة متطابقة.\n• بحث المؤلفين: استرجاع كافة الأوراق المنشورة لباحث محدد من مختلف المستودعات والمجلات العالمية.\n• مطابقة العبارة التامة: مطابقة حرفية غير مجزأة لسلسلة الكلمات المدخلة.\n• التكامل مع الـ DOI: إمكانية فحص أي معرف رقمي مباشرة أو استخراجه من عنوان الدراسة."
                      : "• Keyword Search: Full Boolean syntax (AND, OR, NOT), parentheses grouping, and quotes ('...') for exact phrases.\n• Author Search: Retrieve all publications by a specific scholar across global databases.\n• Exact Phrase: Strict verbatim match for complex scientific terminology.\n• DOI Integration: Direct DOI resolution or title-to-DOI extraction with one click."
                    }
                  </p>
                </div>

                <!-- Card 2: Strict Title Filter -->
                <div className="rounded-[18px] border border-stone-200/80 dark:border-white/10 bg-stone-50/70 dark:bg-white/[0.03] p-4 sm:p-5 space-y-2">
                  <div className="font-black text-[13.5px] text-amber-700 dark:text-amber-400 flex items-center gap-2">
                    <span className="text-base">🎯</span>
                    <span>${lang === "ar" ? "2. فلتر العنوان الإلزامي ودقة الاستهداف 99%" : "2. Strict Title Filter (99% Precision)"}</span>
                  </div>
                  <p className="opacity-85 text-stone-700 dark:text-stone-300 whitespace-pre-line">
                    ${lang === "ar"
                      ? "• مُفعّل (ON): يُلزم محرك البحث بوجود كلماتك صراحةً في عنوان الورقة العلمية (Title)، ويستبعد أي دراسة ذُكرت كلماتها في الملخص فقط. يضمن دقة استهداف تصل إلى 99% للموضوعات المتخصصة مع مسح دفعات تكرارية من قواعد البيانات حتى استيفاء العدد المطلوب.\n• غير مُفعّل (OFF - الافتراضي): بحث استكشافي شامل يبحث في العناوين والملخصات معاً لضمان عدم تفويت أي دراسة قيّمة ذات صلة، مع ترتيب الأوراق المتطابقة في العنوان أولاً."
                      : "• ON: Excludes any paper whose title lacks the exact keywords for 99% precision, continuously fetching batches from engines until your target count is met.\n• OFF (Default): Comprehensive discovery across both titles and abstracts, automatically prioritizing title matches at the top of results."
                    }
                  </p>
                </div>

                <!-- Card 3: Abstracts & Quotas -->
                <div className="rounded-[18px] border border-stone-200/80 dark:border-white/10 bg-stone-50/70 dark:bg-white/[0.03] p-4 sm:p-5 space-y-2">
                  <div className="font-black text-[13.5px] text-indigo-700 dark:text-indigo-400 flex items-center gap-2">
                    <span className="text-base">📑</span>
                    <span>${lang === "ar" ? "3. استخراج الملخصات ونظام الحصص المرنة" : "3. Abstracts Extraction & Flexible Quotas"}</span>
                  </div>
                  <p className="opacity-85 text-stone-700 dark:text-stone-300 whitespace-pre-line">
                    ${lang === "ar"
                      ? "• بحث قياسي (زر الملخصات معطل): يستهلك نقطة واحدة لكل بحث لجلب العناوين والمؤلفين والمجلات وروابط المعرفات والوصول المفتوح فورياً.\n• تفعيل زر الملخصات: يستهلك نقطتين لكل بحث لجلب الملخص الكامل (Abstract) وتضمينه في النتائج وتقرير الـ PDF.\n• الحصص: 50 بحثاً مجانياً للزوار، 250 بحثاً يومياً لحاملي الرمز الثانوي تتجدد تلقائياً كل 24 ساعة، ووصول غير محدود كلياً لأصحاب رموز VIP."
                      : "• Standard Search (Toggle OFF): 1 credit per search for swift metadata, author lists, and DOI links.\n• Include Abstracts (Toggle ON): 2 credits per search (2x rate) to extract complete abstracts into results and PDF dossiers.\n• Quotas: 50 free credits for guests, 250 daily renewing searches for secondary key holders, and unlimited VIP access."
                    }
                  </p>
                </div>

                <!-- Card 4: Reports & PDF Features -->
                <div className="rounded-[18px] border border-stone-200/80 dark:border-white/10 bg-stone-50/70 dark:bg-white/[0.03] p-4 sm:p-5 space-y-2">
                  <div className="font-black text-[13.5px] text-emerald-700 dark:text-emerald-400 flex items-center gap-2">
                    <span className="text-base">📄</span>
                    <span>${lang === "ar" ? "4. تقارير الـ PDF والميزات الحصرية" : "4. PDF Dossiers & Exclusive Features"}</span>
                  </div>
                  <p className="opacity-85 text-stone-700 dark:text-stone-300 whitespace-pre-line">
                    ${lang === "ar"
                      ? "• تقرير موحد شامل: تجميع كافة الأبحاث وملخصاتها وفهارسها وروابطها في ملف PDF واحد متناسق وأنيق.\n• صفحة جديدة لكل بحث: عند استخراج الأبحاث بالملخصات لحاملي الرمز، يبدأ كل بحث في صفحة جديدة مستقلة لقراءة وطباعة أكاديمية مريحة.\n• الحفظ الفوري عند الإيقاف: عند الضغط على زر «إيقاف البحث»، يقوم النظام فوراً بإنتاج ملف الـ PDF متضمناً كافة الأبحاث المجمعة حتى لحظة الإيقاف دون أي فقدان للنتائج."
                      : "• Single Unified Dossier: All papers, abstracts, indices, and links consolidated into a single polished PDF document.\n• New Page per Abstract: For authorized keys, each paper in abstract mode starts on a fresh page for comfortable reading and printing.\n• Graceful Stop & Save: Stopping a search immediately produces the PDF report containing all collected papers up to that exact moment."
                    }
                  </p>
                </div>

                <!-- Card 5: DOI Hub -->
                <div className="rounded-[18px] border border-stone-200/80 dark:border-white/10 bg-stone-50/70 dark:bg-white/[0.03] p-4 sm:p-5 space-y-2">
                  <div className="font-black text-[13.5px] text-cyan-700 dark:text-cyan-400 flex items-center gap-2">
                    <span className="text-base">🔗</span>
                    <span>${lang === "ar" ? "5. منظومة التوثيق ومعرّفات DOI" : "5. DOI Resolution & Matching Hub"}</span>
                  </div>
                  <p className="opacity-85 text-stone-700 dark:text-stone-300 whitespace-pre-line">
                    ${lang === "ar"
                      ? "• فحص معرّف DOI المباشر: فحص واسترجاع البيانات الوصفية الرسمية، وسنة النشر، والمجلة، وروابط التحميل المفتوح لأي معرّف رقمي معتمد.\n• استخراج المعرّف من العنوان: إدخال عنوان أي مقال أو ورقة علمية لمطابقتها في السجلات العالمية واستخراج الـ DOI الرسمي ورابط الوصول لها بدقة متناهية."
                      : "• Direct DOI Lookup: Instant verification of DOIs with official metadata, journal details, publication year, and direct OA links.\n• Title to DOI Matching: Input partial or full paper titles to discover their registered DOI and verified academic source."
                    }
                  </p>
                </div>

                <!-- Card 6: Open Access & BibTeX -->
                <div className="rounded-[18px] border border-stone-200/80 dark:border-white/10 bg-stone-50/70 dark:bg-white/[0.03] p-4 sm:p-5 space-y-2">
                  <div className="font-black text-[13.5px] text-purple-700 dark:text-purple-400 flex items-center gap-2">
                    <span className="text-base">📥</span>
                    <span>${lang === "ar" ? "6. الوصول الحر المفتوح وتوثيق BibTeX" : "6. Open Access & BibTeX Citations"}</span>
                  </div>
                  <p className="opacity-85 text-stone-700 dark:text-stone-300 whitespace-pre-line">
                    ${lang === "ar"
                      ? "• الوصول المفتوح (Open Access): فحص فوري وموثوق عبر بروتوكول Unpaywall لتوفير روابط التنزيل المباشر للملفات الرسمية المفتوحة مجاناً.\n• تصدير مراجع BibTeX: استخراج كود BibTeX القياسي المعتمد لكل بحث بنقرة واحدة، جاهز للاستيراد في برامج إدارة المراجع (Zotero, Mendeley, EndNote) ومستندات LaTeX."
                      : "• Legal Open Access: Real-time verification via Unpaywall to locate freely accessible peer-reviewed full-text PDFs.\n• BibTeX Citation Export: Generate and copy standard BibTeX citation records in one click, ready for Zotero, Mendeley, EndNote, and LaTeX."
                    }
                  </p>
                </div>

              </div>

              <!-- 3. Mobile Optimization & Shortcuts Footer -->
              <div className="pt-4 border-t border-stone-200/60 dark:border-white/10 flex items-center justify-between flex-wrap gap-2 text-[11.5px] opacity-80 font-medium">
                <div className="flex items-center gap-2">
                  <span>📱</span>
                  <span>${lang === "ar" ? "المنصة مُحسّنة بالكامل لجميع شاشات الهواتف الذكية والأجهزة اللوحية والمكتبية" : "Fully responsive and optimized for mobile phones, tablets, and desktops"}</span>
                </div>
                <div className="flex items-center gap-2 font-mono">
                  <span>⌨️</span>
                  <span>${lang === "ar" ? "Ctrl + Enter: للبحث الفوري | Esc: لإغلاق النوافذ" : "Ctrl + Enter: Quick Search | Esc: Close Modals"}</span>
                </div>
              </div>

            </div>
          </div>
        </main>

        <!-- Modal Pop-up on Completion -->
        ${showModal ? html`
          <div
            className="fixed inset-0 z-50 grid place-items-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in cursor-pointer"
            onClick=${(e) => {
              if (e.target === e.currentTarget) {
                setShowModal(false);
              }
            }}
          >
            <div
              onClick=${(e) => e.stopPropagation()}
              className=${`w-full max-w-[480px] rounded-[24px] border shadow-2xl p-6 md:p-7 glass-panel relative cursor-default ${
                isDark ? "bg-[#1a1816]/95 border-white/15 text-white" : "bg-white/95 border-stone-200 text-stone-900"
              }`}
            >
              <!-- Close Button (X) -->
              <button
                type="button"
                onClick=${() => setShowModal(false)}
                className="absolute top-5 left-5 h-8 w-8 rounded-full bg-stone-100 hover:bg-stone-200 dark:bg-white/10 dark:hover:bg-white/20 grid place-items-center text-stone-600 dark:text-stone-300 font-black text-sm transition cursor-pointer"
                title=${lang === "ar" ? "إغلاق النافذة والمتابعة" : "Close window and continue"}
              >
                ✕
              </button>

              <div className="h-14 w-14 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-300 grid place-items-center mb-4 text-[26px] shadow-sm">
                ✓
              </div>
              <h4 className="text-[17px] font-black">${doneTitle}</h4>
              <p className="text-[13px] opacity-80 mt-2 leading-6">
                ${isLocal
                  ? (lang === "ar" ? "تم استخراج الأبحاث بنجاح وحفظ الحزمة المضغوطة مباشرة على جهازك، ويمكنك تصفح الأبحاث المستخرجة مباشرة أدناه." : "Papers successfully extracted and package saved directly to your computer. You can explore extracted papers directly below.")
                  : (lang === "ar" ? "تمت عملية المسح بنجاح وفهرسة وتجميع الأوراق في حزمة ZIP كاملة." : "Search, indexing, and packaging into full ZIP archive completed successfully.")}
              </p>

              <!-- Local Save Path Display in Modal -->
              ${isLocal && savePath ? html`
                <div className="mt-4 rounded-[14px] border border-stone-200 dark:border-white/15 bg-black/5 dark:bg-white/5 p-3.5 space-y-2 text-right">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[12px] font-bold opacity-80 flex items-center gap-1">
                      📁 ${lang === "ar" ? "مسار الحفظ على جهازك:" : "Local Save Path:"}
                    </span>
                    <button
                      type="button"
                      onClick=${() => copyToClipboard(savePath, () => {
                        setCopiedPath(true);
                        setTimeout(() => setCopiedPath(false), 3000);
                      })}
                      className="text-[11px] px-2.5 py-1 rounded-lg bg-stone-900 text-white dark:bg-white dark:text-black font-bold hover:opacity-85 transition shadow-sm cursor-pointer"
                    >
                      ${copiedPath ? (lang === "ar" ? "✓ تم النسخ" : "✓ Copied") : (lang === "ar" ? "📋 نسخ المسار" : "📋 Copy Path")}
                    </button>
                  </div>
                  <div className="text-[11px] font-mono select-all break-all bg-white dark:bg-black/40 p-2.5 rounded-lg border border-stone-200 dark:border-white/10 text-left text-stone-800 dark:text-stone-200" dir="ltr">
                    ${savePath}
                  </div>
                </div>
              ` : null}

              <div className="mt-6 flex flex-col gap-2">
                <a
                  href=${downloadUrl}
                  download=${filename || (fileType === "pdf" ? "Academic_Report.pdf" : "Academic_Archive.zip")}
                  className="w-full h-[46px] rounded-[14px] bg-emerald-600 hover:bg-emerald-700 text-white flex items-center justify-center gap-2 text-[14px] font-black transition shadow-sm cursor-pointer"
                  title=${lang === "ar" ? "تحميل وتنزيل الملف مباشرة إلى جهازك" : "Download file directly"}
                >
                  <span>📥</span> ${lang === "ar" ? (fileType === "pdf" ? "تحميل التقرير (PDF)" : "تحميل الحزمة (ZIP)") : (fileType === "pdf" ? "Download Report (PDF)" : "Download Archive (ZIP)")}
                </a>
                <button
                  type="button"
                  onClick=${() => setShowModal(false)}
                  className="w-full h-[42px] rounded-[14px] border border-stone-200 dark:border-white/15 text-[13px] font-bold hover:bg-stone-100 dark:hover:bg-white/10 transition cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <span>📋</span> ${lang === "ar" ? "عرض نتائج الأبحاث في الصفحة" : "View Results on Page"}
                </button>
              </div>
            </div>
          </div>
        ` : null}

        <!-- Abstract Details Modal -->
        ${showAbstractModal && abstractModalPaper ? html`
          <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 backdrop-blur-md p-4 animate-fade-in">
            <div className=${`w-full max-w-[760px] max-h-[90vh] flex flex-col rounded-[24px] border shadow-2xl glass-panel ${
              isDark ? "bg-[#181614]/98 border-white/20 text-white" : "bg-white/98 border-stone-200 text-stone-900"
            }`}>
              <!-- Modal Header -->
              <div className="p-6 pb-4 border-b border-stone-200/60 dark:border-white/10 flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className=${`text-[11px] px-2.5 py-0.5 rounded-full font-bold border ${
                      (abstractModalPaper.is_preprint || abstractModalPaper.source === "arxiv" || abstractModalPaper.source === "biorxiv" || abstractModalPaper.source === "medrxiv")
                        ? "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300 border-amber-300 dark:border-amber-800"
                        : "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800"
                    }`}>
                      ${(abstractModalPaper.is_preprint || abstractModalPaper.source === "arxiv" || abstractModalPaper.source === "biorxiv" || abstractModalPaper.source === "medrxiv") ? t.preprint : t.peerReviewed}
                    </span>
                    ${abstractModalPaper.year && abstractModalPaper.year !== "0000" ? html`
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-stone-100 dark:bg-white/10 font-sans font-bold">
                        ${abstractModalPaper.year}
                      </span>
                    ` : null}
                    ${abstractModalPaper.journal ? html`
                      <span className="text-[11px] opacity-75 font-semibold">
                        📖 ${abstractModalPaper.journal}
                      </span>
                    ` : null}
                  </div>
                  <h3 className="text-[17px] font-black leading-snug mt-2" dir="ltr">
                    ${abstractModalPaper.title || "No Title"}
                  </h3>
                  <div className="text-[12px] opacity-75 truncate max-w-[600px]" dir="ltr">
                    👤 ${(abstractModalPaper.authors && abstractModalPaper.authors.length) ? abstractModalPaper.authors.join(", ") : "Unknown Authors"}
                  </div>
                </div>
                <button
                  type="button"
                  onClick=${() => setShowAbstractModal(false)}
                  className="h-9 w-9 rounded-full bg-stone-100 dark:bg-white/10 hover:bg-stone-200 dark:hover:bg-white/20 grid place-items-center text-[16px] font-black transition cursor-pointer flex-shrink-0"
                >
                  ✕
                </button>
              </div>

              <!-- Modal Body (Abstract text) -->
              <div className="p-6 overflow-y-auto space-y-4 text-right flex-1">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[13px] font-black flex items-center gap-1.5 text-blue-600 dark:text-blue-400">
                    <span>📄</span> ${lang === "ar" ? "ملخص البحث (Abstract):" : "Paper Abstract:"}
                  </div>
                  ${abstractModalPaper.abstract && abstractModalPaper.abstract !== "No abstract provided in source metadata." ? html`
                    <button
                      type="button"
                      onClick=${() => copyToClipboard(abstractModalPaper.abstract, () => {
                        setCopiedModalAbstract(true);
                        setTimeout(() => setCopiedModalAbstract(false), 2500);
                      })}
                      className="text-[11px] px-3 py-1 rounded-lg bg-stone-100 dark:bg-white/10 hover:bg-stone-200 dark:hover:bg-white/20 font-bold transition flex items-center gap-1 cursor-pointer"
                    >
                      ${copiedModalAbstract ? (lang === "ar" ? "✓ تم نسخ الملخص" : "✓ Abstract Copied") : (lang === "ar" ? "📋 نسخ الملخص" : "📋 Copy Abstract")}
                    </button>
                  ` : null}
                </div>

                <div className="rounded-[16px] bg-stone-50 dark:bg-black/40 border border-stone-200/80 dark:border-white/10 p-5 text-left" dir="ltr">
                  ${abstractModalPaper.abstract && abstractModalPaper.abstract !== "No abstract provided in source metadata." ? html`
                    <p className="text-[13px] leading-relaxed text-stone-800 dark:text-stone-200 whitespace-pre-wrap font-sans">
                      ${abstractModalPaper.abstract}
                    </p>
                  ` : html`
                    <p className="text-[13px] italic opacity-60">
                      No abstract provided in source metadata for this paper.
                    </p>
                  `}
                </div>

                <!-- Links & DOIs in modal -->
                <div className="pt-2 flex flex-wrap items-center justify-between gap-3 text-[12px]">
                  <div className="flex items-center gap-3">
                    ${abstractModalPaper.doi ? html`
                      <a
                        href=${`https://doi.org/${abstractModalPaper.doi}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 dark:text-blue-400 font-mono font-bold hover:underline"
                        dir="ltr"
                      >
                        🔗 DOI: ${abstractModalPaper.doi}
                      </a>
                    ` : null}
                    ${(abstractModalPaper.oa_url || abstractModalPaper.url) ? html`
                      <a
                        href=${abstractModalPaper.oa_url || abstractModalPaper.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-emerald-600 dark:text-emerald-400 font-bold hover:underline"
                      >
                        ↗ ${lang === "ar" ? "الرابط المباشر" : "Direct Link"}
                      </a>
                    ` : null}
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick=${() => {
                        const apa = generateAPA(abstractModalPaper);
                        copyRichCitation(apa, abstractModalPaper.apa_html, () => showAlert(lang === "ar" ? "تم نسخ توثيق APA 7th للوورد بنجاح!" : "Formatted APA 7th copied for Word!", "success", 2000));
                      }}
                      className="px-3 py-1.5 rounded-lg border border-purple-200 dark:border-purple-800/60 bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 text-[11px] font-bold hover:bg-purple-100 dark:hover:bg-purple-900/60 cursor-pointer shadow-sm"
                      title=${abstractModalPaper.apa_plain || apaToPlainText(generateAPA(abstractModalPaper))}
                    >
                      📋 APA 7th
                    </button>
                    <button
                      type="button"
                      onClick=${() => {
                        const bib = generateBibTeX(abstractModalPaper);
                        copyToClipboard(bib, () => showAlert(lang === "ar" ? "تم نسخ كود BibTeX!" : "BibTeX citation copied!", "info", 2000));
                      }}
                      className="px-3 py-1.5 rounded-lg border border-stone-300 dark:border-white/20 text-[11px] font-mono font-bold hover:bg-stone-100 dark:hover:bg-white/10 cursor-pointer"
                    >
                      📋 BibTeX
                    </button>
                  </div>
                </div>
              </div>

              <!-- Modal Footer -->
              <div className="p-4 border-t border-stone-200/60 dark:border-white/10 flex justify-end">
                <button
                  type="button"
                  onClick=${() => setShowAbstractModal(false)}
                  className="px-5 py-2 rounded-[12px] bg-stone-900 text-white dark:bg-white dark:text-black font-bold text-[12px] hover:opacity-90 cursor-pointer"
                >
                  ${lang === "ar" ? "إغلاق" : "Close"}
                </button>
              </div>
            </div>
          </div>
        ` : null}

        <!-- First-Run Onboarding Modal -->
        ${showFirstRunModal ? html`
          <div className="fixed inset-0 z-50 grid place-items-center bg-black/75 p-4 animate-fade-in">
            <div className=${`w-full max-w-[640px] max-h-[92vh] flex flex-col rounded-[26px] border shadow-2xl overflow-hidden glass-panel ${
              isDark ? "bg-[#161513]/98 border-white/20 text-white" : "bg-white/98 border-stone-200 text-stone-900"
            }`}>
              <!-- Modal Header -->
              <div className="p-6 pb-4 border-b border-stone-200/60 dark:border-white/10 flex items-center gap-3.5">
                <div className="h-12 w-12 rounded-[16px] bg-blue-600/15 text-blue-600 dark:text-blue-400 grid place-items-center text-2xl flex-shrink-0">
                  🌊
                </div>
                <div>
                  <h3 className="text-[18px] font-black leading-tight">${lang === "ar" ? "مرحباً بك في محيط المعرفة" : "Welcome to Knowledge Ocean"}</h3>
                  <p className="text-[12px] opacity-75 font-medium mt-0.5">${lang === "ar" ? "منصة الاسترجاع والتوثيق الأكاديمي فائق الدقة (إعدادات الباحث)" : "High-Precision Academic Retrieval & Documentation System (Researcher Setup)"}</p>
                </div>
              </div>

              <!-- Modal Body -->
              <div className="p-6 space-y-5 overflow-y-auto max-h-[65vh]">
                <!-- Email Field -->
                <div className="space-y-1.5">
                  <label className="block text-[13px] font-black">
                    ${lang === "ar" ? "📧 البريد الإلكتروني للباحث (User Email):" : "📧 Researcher Email (Polite Pool):"}
                  </label>
                  <input
                    type="email"
                    dir="ltr"
                    value=${settingsEmail}
                    onInput=${(e) => setSettingsEmail(e.target.value)}
                    placeholder="researcher@example.com"
                    className="w-full h-[44px] px-4 rounded-[14px] border border-stone-300 dark:border-white/20 bg-stone-50 dark:bg-black/30 text-sm font-sans focus:outline-none focus:ring-2 focus:ring-blue-500 text-stone-900 dark:text-white"
                  />
                  <p className="text-[11px] opacity-70 leading-relaxed">
                    ${lang === "ar" ? "يُستخدم في بروتوكول Polite Pool لخدمة Unpaywall لتسريع استخراج روابط الوصول الحر (Open Access) قانونياً." : "Used in the Polite Pool protocol for Unpaywall and Crossref to accelerate Open Access link retrieval."}
                  </p>
                </div>

                <!-- Elsevier API Key Field -->
                <div className="space-y-2">
                  <label className="block text-[13px] font-black">
                    ${lang === "ar" ? "🔑 مفتاح إلسيفير الأكاديمي (Elsevier / Scopus API Key) — " : "🔑 Scopus / Elsevier API Key — "}<span className="text-blue-600 dark:text-blue-400 font-bold">${lang === "ar" ? "اختياري" : "Optional"}</span>:
                  </label>
                  <input
                    type="text"
                    dir="ltr"
                    value=${settingsElsevierKey}
                    onInput=${(e) => setSettingsElsevierKey(e.target.value)}
                    placeholder=${lang === "ar" ? "أدخل مفتاحك الأكاديمي إن وجد، أو اتركه فارغاً" : "Enter your academic API key if available, or leave blank"}
                    className="w-full h-[44px] px-4 rounded-[14px] border border-stone-300 dark:border-white/20 bg-stone-50 dark:bg-black/30 text-sm font-sans focus:outline-none focus:ring-2 focus:ring-blue-500 text-stone-900 dark:text-white"
                  />

                  <!-- Explanatory Notice required by user -->
                  <div className="p-4 rounded-[16px] bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800/60 text-[12px] leading-relaxed space-y-1.5">
                    <div className="font-black text-blue-900 dark:text-blue-300 flex items-center gap-1.5">
                      <span>💡</span> ${lang === "ar" ? "تنبيه هام حول مستوعب سكوباس (Scopus):" : "Important Notice regarding Scopus:"}
                    </div>
                    <div className="text-blue-950/90 dark:text-blue-200/90 font-medium">
                      ${lang === "ar" ? "للوصول المباشر إلى أبحاث قاعدة سكوباس (Scopus / ScienceDirect) يرجى إدخال مفتاح API الخاص بك. يمكنك تركه فارغاً والاعتماد التام على المستوعبات الأكاديمية التسعة الأخرى (arXiv, PubMed, Crossref, Semantic Scholar, CORE, OpenAlex, وغيرها)، مع إمكانية إضافته أو تعديله لاحقاً في أي وقت عبر نافذة الإعدادات ⚙️." : "For direct access to Scopus / ScienceDirect papers, please enter your API key. You may leave it blank and rely fully on the other open academic engines (arXiv, PubMed, Crossref, Semantic Scholar, CORE, OpenAlex, etc.), and you can add or update it anytime via Settings ⚙️."}
                    </div>
                  </div>
                </div>

                ${settingsStatusMsg ? html`
                  <div className=${`p-3 rounded-[12px] text-xs font-bold text-center ${
                    settingsStatusMsg.type === "success" ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-200" : "bg-red-100 dark:bg-red-950 text-red-800 dark:text-red-200"
                  }`}>
                    ${settingsStatusMsg.text}
                  </div>
                ` : null}
              </div>

              <!-- Modal Footer -->
              <div className="p-4 px-6 border-t border-stone-200/60 dark:border-white/10 flex items-center justify-between gap-3 bg-stone-50/50 dark:bg-black/20">
                <button
                  type="button"
                  onClick=${() => {
                    try { localStorage.setItem("ko_first_run_completed", "true"); } catch(e){}
                    setShowFirstRunModal(false);
                  }}
                  className="px-4 py-2.5 rounded-[12px] text-xs font-bold text-stone-600 dark:text-stone-300 hover:bg-stone-200 dark:hover:bg-white/10 transition cursor-pointer"
                >
                  ${lang === "ar" ? "تخطي الآن والبدء مباشرة" : "Skip for now & start"}
                </button>
                <button
                  type="button"
                  disabled=${settingsSaving}
                  onClick=${() => saveSettings(settingsEmail, settingsElsevierKey, true)}
                  className="px-6 py-2.5 rounded-[12px] bg-blue-600 hover:bg-blue-700 text-white text-xs font-black shadow-md transition disabled:opacity-50 cursor-pointer flex items-center gap-2"
                >
                  ${settingsSaving ? (lang === "ar" ? "جاري الحفظ..." : "Saving...") : (lang === "ar" ? "💾 حفظ الإعدادات ومتابعة" : "💾 Save & Continue")}
                </button>
              </div>
            </div>
          </div>
        ` : null}

        <!-- Settings & Sources Modal -->
        ${showSettingsModal ? html`
          <div className="fixed inset-0 z-50 grid place-items-center bg-black/75 p-4 animate-fade-in">
            <div className=${`w-full max-w-[680px] max-h-[92vh] flex flex-col rounded-[26px] border shadow-2xl overflow-hidden glass-panel ${
              isDark ? "bg-[#161513]/98 border-white/20 text-white" : "bg-white/98 border-stone-200 text-stone-900"
            }`}>
              <!-- Modal Header -->
              <div className="p-6 pb-4 border-b border-stone-200/60 dark:border-white/10 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-[14px] bg-stone-100 dark:bg-white/10 grid place-items-center text-xl">
                    ⚙️
                  </div>
                  <div>
                    <h3 className="text-[17px] font-black leading-tight">${lang === "ar" ? "إعدادات الباحث ومستوعبات البحث" : "Researcher Settings & Academic Sources"}</h3>
                    <p className="text-[11px] opacity-75 font-medium mt-0.5">${lang === "ar" ? "عرض وتعديل بيانات الاتصال ومفاتيح المستوعبات وحفظها تلقائياً" : "View and modify contact info and repository keys"}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick=${() => setShowSettingsModal(false)}
                  className="h-8 w-8 rounded-full border border-stone-200 dark:border-white/15 grid place-items-center text-sm hover:bg-stone-100 dark:hover:bg-white/10 transition cursor-pointer"
                >
                  ✕
                </button>
              </div>

              <!-- Modal Body -->
              <div className="p-6 space-y-5 overflow-y-auto max-h-[65vh]">
                <!-- Email Field -->
                <div className="space-y-1.5">
                  <label className="block text-[13px] font-black">
                    ${lang === "ar" ? "📧 البريد الإلكتروني (User Email):" : "📧 Email (Polite Pool):"}
                  </label>
                  <input
                    type="email"
                    dir="ltr"
                    value=${settingsEmail}
                    onInput=${(e) => setSettingsEmail(e.target.value)}
                    placeholder="researcher@example.com"
                    className="w-full h-[42px] px-4 rounded-[12px] border border-stone-300 dark:border-white/20 bg-stone-50 dark:bg-black/30 text-sm font-sans focus:outline-none focus:ring-2 focus:ring-blue-500 text-stone-900 dark:text-white"
                  />
                  <p className="text-[11px] opacity-70">
                    ${lang === "ar" ? "مخصص لخدمة Unpaywall لتسريع جلب روابط الـ Open Access الرسمية." : "Used for polite pooling with Unpaywall to accelerate Open Access discovery."}
                  </p>
                </div>

                <!-- Elsevier API Key -->
                <div className="space-y-1.5">
                  <label className="block text-[13px] font-black">
                    ${lang === "ar" ? "🔑 مفتاح إلسيفير (Elsevier / Scopus API Key) — " : "🔑 Elsevier / Scopus API Key — "}<span className="text-blue-600 dark:text-blue-400 font-bold">${lang === "ar" ? "اختياري" : "Optional"}</span>:
                  </label>
                  <input
                    type="text"
                    dir="ltr"
                    value=${settingsElsevierKey}
                    onInput=${(e) => setSettingsElsevierKey(e.target.value)}
                    placeholder=${t.settingsElsevierPlaceholder}
                    className="w-full h-[42px] px-4 rounded-[12px] border border-stone-300 dark:border-white/20 bg-stone-50 dark:bg-black/30 text-sm font-sans focus:outline-none focus:ring-2 focus:ring-blue-500 text-stone-900 dark:text-white"
                  />
                  <div className="p-3 rounded-[12px] bg-stone-100 dark:bg-white/5 border border-stone-200/70 dark:border-white/10 text-[11px] leading-relaxed">
                    ${t.settingsElsevierNote}
                  </div>
                </div>

                <!-- Provider Status Grid -->
                <div className="space-y-2 pt-2 border-t border-stone-200/60 dark:border-white/10">
                  <h4 className="text-[12px] font-black text-stone-500 dark:text-stone-400">
                    ${t.settingsStatusHeader}
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
                    <div className=${`p-2.5 rounded-[10px] border flex items-center justify-between ${
                      settingsElsevierKey ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200" : "bg-stone-100 dark:bg-white/5 border-stone-200 dark:border-white/10 opacity-75"
                    }`}>
                      <span className="font-bold">Scopus / Elsevier</span>
                      <span className="font-black text-[10px]">${settingsElsevierKey ? t.statusConnected : t.statusInactive}</span>
                    </div>
                    <div className="p-2.5 rounded-[10px] border bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 flex items-center justify-between">
                      <span className="font-bold">arXiv</span>
                      <span className="font-black text-[10px]">${t.statusActive}</span>
                    </div>
                    <div className="p-2.5 rounded-[10px] border bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 flex items-center justify-between">
                      <span className="font-bold">PubMed (NCBI)</span>
                      <span className="font-black text-[10px]">${t.statusActive}</span>
                    </div>
                    <div className="p-2.5 rounded-[10px] border bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 flex items-center justify-between">
                      <span className="font-bold">Crossref</span>
                      <span className="font-black text-[10px]">${t.statusActive}</span>
                    </div>
                    <div className="p-2.5 rounded-[10px] border bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 flex items-center justify-between">
                      <span className="font-bold">Semantic Scholar</span>
                      <span className="font-black text-[10px]">${t.statusActive}</span>
                    </div>
                    <div className="p-2.5 rounded-[10px] border bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 flex items-center justify-between">
                      <span className="font-bold">OpenAlex</span>
                      <span className="font-black text-[10px]">${t.statusActive}</span>
                    </div>
                    <div className="p-2.5 rounded-[10px] border bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 flex items-center justify-between">
                      <span className="font-bold">CORE UK</span>
                      <span className="font-black text-[10px]">${t.statusActive}</span>
                    </div>
                    <div className="p-2.5 rounded-[10px] border bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 flex items-center justify-between">
                      <span className="font-bold">Unpaywall OA</span>
                      <span className="font-black text-[10px]">${t.statusActive}</span>
                    </div>
                    <div className="p-2.5 rounded-[10px] border bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 flex items-center justify-between">
                      <span className="font-bold">bioRxiv / medRxiv</span>
                      <span className="font-black text-[10px]">${t.statusActive}</span>
                    </div>
                  </div>
                </div>



                ${settingsStatusMsg ? html`
                  <div className=${`p-3 rounded-[12px] text-xs font-bold text-center ${
                    settingsStatusMsg.type === "success" ? "bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-200" : "bg-red-100 dark:bg-red-950 text-red-800 dark:text-red-200"
                  }`}>
                    ${settingsStatusMsg.text}
                  </div>
                ` : null}
              </div>

              <!-- Modal Footer -->
              <div className="p-4 px-6 border-t border-stone-200/60 dark:border-white/10 flex items-center justify-between gap-3 bg-stone-50/50 dark:bg-black/20">
                <button
                  type="button"
                  onClick=${() => setShowSettingsModal(false)}
                  className="px-4 py-2.5 rounded-[12px] text-xs font-bold text-stone-600 dark:text-stone-300 hover:bg-stone-200 dark:hover:bg-white/10 transition cursor-pointer"
                >
                  ${lang === "ar" ? "إغلاق" : "Close"}
                </button>
                <button
                  type="button"
                  disabled=${settingsSaving}
                  onClick=${() => saveSettings(settingsEmail, settingsElsevierKey, false)}
                  className="px-6 py-2.5 rounded-[12px] bg-blue-600 hover:bg-blue-700 text-white text-xs font-black shadow-md transition disabled:opacity-50 cursor-pointer flex items-center gap-2"
                >
                  ${settingsSaving ? t.savingBtn : t.saveSettingsBtn}
                </button>
              </div>
            </div>
          </div>
        ` : null}

        <!-- Login / VIP & Secondary Code Modal -->
        ${showLoginModal ? html`
          <div className="fixed inset-0 z-50 grid place-items-center bg-black/75 p-4 animate-fade-in backdrop-blur-sm">
            <div className=${`w-full max-w-[520px] max-h-[92vh] flex flex-col rounded-[26px] border shadow-2xl overflow-hidden glass-panel ${
              isDark ? "bg-[#161513]/98 border-white/20 text-white" : "bg-white/98 border-stone-200 text-stone-900"
            }`}>
              <!-- Modal Header -->
              <div className="p-6 pb-4 border-b border-stone-200/60 dark:border-white/10 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-[14px] bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 grid place-items-center text-xl shadow-sm">
                    🔐
                  </div>
                  <div>
                    <h3 className="text-[17px] font-black leading-tight">
                      ${lang === "ar" ? "تسجيل الدخول / الرمز الثانوي و VIP" : "Sign In / VIP & Secondary Code"}
                    </h3>
                    <p className="text-[11px] opacity-75 font-medium mt-0.5">
                      ${lang === "ar" ? "تفعيل حصة 250 بحثاً يومياً أو الوصول الشامل غير المحدود" : "Activate 250 daily searches or unlimited access"}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick=${() => setShowLoginModal(false)}
                  className="h-8 w-8 rounded-full border border-stone-200 dark:border-white/15 grid place-items-center text-sm hover:bg-stone-100 dark:hover:bg-white/10 transition cursor-pointer"
                >
                  ✕
                </button>
              </div>

              <div className="p-6 space-y-4 overflow-y-auto max-h-[70vh]">
                <!-- Active Account Status (If already logged in) -->
                ${password ? html`
                  <div className=${`p-4 rounded-[18px] border flex items-start gap-3.5 ${
                    quota.isVip
                      ? "bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-200"
                      : "bg-teal-500/10 border-teal-500/30 text-teal-900 dark:text-teal-200"
                  }`}>
                    <span className="text-2xl shrink-0">${quota.isVip ? "✨" : "🔄"}</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-black text-sm">
                        ${quota.isVip
                          ? (lang === "ar" ? "حساب VIP نشط (استخراج غير محدود)" : "Active VIP Tier (Unlimited Access)")
                          : (lang === "ar" ? "الرمز الثانوي نشط (250 بحث يومياً)" : "Active Secondary Tier (250 Daily Searches)")}
                      </div>
                      <p className="text-xs opacity-85 mt-1 leading-relaxed">
                        ${quota.isVip
                          ? (lang === "ar" ? "تتمتع بصلاحية وصول مفتوحة بالكامل بدون أي قيود يومية على عدد الأبحاث والملخصات." : "Full unlimited downloads and abstracts with zero daily caps.")
                          : (lang === "ar" ? `رصيدك اليومي المتبقي: ${quota.remaining} من 250 بحثاً (يتجدد يومياً عند 12:00 ص بتوقيت بغداد).` : `Remaining daily quota: ${quota.remaining} of 250 searches (Renews at 12:00 AM Baghdad time).`)}
                      </p>
                      <button
                        type="button"
                        onClick=${handleLogout}
                        className="mt-3 px-3.5 py-1.5 rounded-[10px] bg-red-600/10 hover:bg-red-600/20 text-red-600 dark:text-red-400 border border-red-600/30 text-xs font-bold transition cursor-pointer flex items-center gap-1.5"
                      >
                        <span>🚪</span>
                        <span>${lang === "ar" ? "تسجيل الخروج (العودة للوضع المجاني 50)" : "Log Out (Switch to Guest 50)"}</span>
                      </button>
                    </div>
                  </div>
                ` : null}

                <!-- Code Info Cards -->
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                  <div className="p-3 rounded-[14px] border border-stone-200 dark:border-white/10 bg-stone-50 dark:bg-black/30">
                    <div className="font-bold flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
                      <span>✨</span>
                      <span>${lang === "ar" ? "مفتاح VIP الأكاديمي" : "Academic VIP Key"}</span>
                    </div>
                    <div className="opacity-75 text-[11px] mt-1">
                      ${lang === "ar" ? "استخراج شامل وغير محدود للأبحاث والملخصات وقواعد Scopus." : "Unlimited downloads, full abstracts, and Scopus access."}
                    </div>
                  </div>
                  <div className="p-3 rounded-[14px] border border-stone-200 dark:border-white/10 bg-stone-50 dark:bg-black/30">
                    <div className="font-bold flex items-center gap-1.5 text-teal-600 dark:text-teal-400">
                      <span>🔄</span>
                      <span>${lang === "ar" ? "الرمز الثانوي المتجدد" : "Renewable Secondary Key"}</span>
                    </div>
                    <div className="opacity-75 text-[11px] mt-1">
                      ${lang === "ar" ? "حصة يومية 250 بحثاً تتجدد 12:00 ص بتوقيت بغداد." : "250 searches daily renewing 12:00 AM Baghdad time."}
                    </div>
                  </div>
                </div>

                <!-- 24-Hour IP Ban Anti-Brute-Force Notice -->
                <div className="p-3 rounded-[14px] bg-amber-50 dark:bg-amber-950/30 border border-amber-300 dark:border-amber-800/60 text-amber-900 dark:text-amber-200 text-xs flex items-start gap-2.5">
                  <span className="text-base shrink-0">🛡️</span>
                  <div className="leading-relaxed">
                    <span className="font-bold">${lang === "ar" ? "حماية ضد التخمين الآلي:" : "Anti-Bot Brute Force Protection:"} </span>
                    <span className="opacity-90">
                      ${lang === "ar" ? "يتم حظر عنوان IP تلقائياً لمدة 24 ساعة عند إدخال 5 محاولات خاطئة متتالية." : "IP address is banned automatically for 24 hours after 5 consecutive failed attempts."}
                    </span>
                  </div>
                </div>

                <!-- Banned Alert or Error Message -->
                ${isIpBanned ? html`
                  <div className="p-3.5 rounded-[14px] bg-rose-50 dark:bg-rose-950/50 border-2 border-rose-500 text-rose-800 dark:text-rose-200 text-xs font-bold space-y-1">
                    <div className="flex items-center gap-2 text-sm text-rose-600 dark:text-rose-400 font-black">
                      <span>🚫</span>
                      <span>${lang === "ar" ? "تم حظر هذا الـ IP لمدة 24 ساعة" : "IP Address Temporarily Banned for 24h"}</span>
                    </div>
                    <p className="opacity-90 font-normal">
                      ${loginError || (lang === "ar" ? "تم تجاوز الحد الأقصى للمحاولات الخاطئة (5 محاولات). يرجى الانتظار لحين انتهاء مدة الحظر." : "Maximum failed attempts reached. Please wait until the ban expires.")}
                    </p>
                  </div>
                ` : loginError ? html`
                  <div className="p-3.5 rounded-[14px] bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs font-bold flex items-center justify-between gap-2">
                    <span>${loginError}</span>
                    ${loginAttemptsLeft !== null ? html`
                      <span className="px-2 py-0.5 rounded-full bg-rose-200 dark:bg-rose-900 text-rose-900 dark:text-rose-100 text-[10px] font-black shrink-0">
                        ${lang === "ar" ? `متبقي ${loginAttemptsLeft}` : `${loginAttemptsLeft} left`}
                      </span>
                    ` : null}
                  </div>
                ` : null}

                ${loginSuccessMsg ? html`
                  <div className="p-3.5 rounded-[14px] bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-xs font-bold text-center">
                    ${loginSuccessMsg}
                  </div>
                ` : null}

                <!-- Code Input Field -->
                <div className="space-y-1.5 pt-1">
                  <label className="block text-xs font-bold text-stone-700 dark:text-stone-300">
                    ${lang === "ar" ? "أدخل رمز المرور أو مفتاح VIP:" : "Enter Access Code or VIP Key:"}
                  </label>
                  <div className="relative">
                    <input
                      type=${loginShowPassword ? "text" : "password"}
                      dir="ltr"
                      disabled=${isIpBanned || loginLoading}
                      value=${loginInputCode}
                      onInput=${(e) => setLoginInputCode(e.target.value)}
                      onKeyDown=${(e) => { if (e.key === "Enter") handleLogin(); }}
                      placeholder=${lang === "ar" ? "رمز VIP أو الرمز الثانوي..." : "VIP or secondary key..."}
                      className="w-full h-[46px] px-4 pr-11 pl-4 rounded-[14px] border border-stone-300 dark:border-white/20 bg-stone-50 dark:bg-black/40 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 text-stone-900 dark:text-white disabled:opacity-50"
                    />
                    <button
                      type="button"
                      tabIndex="-1"
                      onClick=${() => setLoginShowPassword(!loginShowPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-700 dark:hover:text-stone-200 text-base cursor-pointer"
                      title=${loginShowPassword ? "إخفاء" : "إظهار"}
                    >
                      ${loginShowPassword ? "🙈" : "👁️"}
                    </button>
                  </div>
                </div>
              </div>

              <!-- Modal Footer -->
              <div className="p-4 px-6 border-t border-stone-200/60 dark:border-white/10 flex items-center justify-between gap-3 bg-stone-50/50 dark:bg-black/20">
                <button
                  type="button"
                  onClick=${() => setShowLoginModal(false)}
                  className="px-4 py-2.5 rounded-[12px] text-xs font-bold text-stone-600 dark:text-stone-300 hover:bg-stone-200 dark:hover:bg-white/10 transition cursor-pointer"
                >
                  ${lang === "ar" ? "إغلاق" : "Close"}
                </button>
                <button
                  type="button"
                  disabled=${isIpBanned || loginLoading || !loginInputCode.trim()}
                  onClick=${() => handleLogin()}
                  className="px-6 py-2.5 rounded-[12px] bg-blue-600 hover:bg-blue-700 text-white text-xs font-black shadow-md transition disabled:opacity-50 cursor-pointer flex items-center gap-2"
                >
                  ${loginLoading ? (lang === "ar" ? "جاري التحقق..." : "Verifying...") : (lang === "ar" ? "🔑 تسجيل الدخول / تفعيل" : "🔑 Sign In / Activate")}
                </button>
              </div>
            </div>
          </div>
        ` : null}

        <!-- Footer -->
        <footer className="mx-auto max-w-[1440px] px-8 py-10 text-center space-y-3 font-sans">
          <div dir="ltr" className="text-[13px] font-bold text-stone-800 dark:text-stone-200 tracking-wide">
            Developed by ABDULSALAM <span className="mx-1">S.</span> HASAN
          </div>

          <!-- Telegram Error Reporting Button & Link -->
          <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
            <span className="text-xs text-stone-600 dark:text-stone-400 font-medium">
              ${lang === "ar" ? "أبلغ عن أي أخطاء في الموقع على تلكرام:" : "Report any website errors on Telegram:"}
            </span>
            <a
              href="https://t.me/knowledgeocean123_bot"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#229ED9]/15 hover:bg-[#229ED9]/25 text-[#229ED9] dark:text-[#38bdf8] border border-[#229ED9]/30 hover:border-[#229ED9]/60 transition-all duration-200 text-xs font-bold shadow-sm group cursor-pointer"
              title=${lang === "ar" ? "تواصل على تلكرام للإبلاغ عن أي خطأ أو مشكلة في الموقع" : "Contact on Telegram to report website bugs"}
            >
              <svg className="w-4 h-4 text-[#229ED9] dark:text-[#38bdf8] fill-current group-hover:scale-110 transition-transform" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.19-.08-.05-.19-.02-.27 0-.12.03-1.99 1.27-5.62 3.72-.53.36-1.01.54-1.44.53-.47-.01-1.38-.27-2.05-.49-.83-.27-1.49-.42-1.43-.88.03-.24.38-.49 1.03-.75 4.04-1.76 6.74-2.92 8.09-3.48 3.85-1.6 4.65-1.88 5.17-1.89.11 0 .37.03.54.17.14.12.18.28.2.45-.02.07-.02.13-.03.22z"/>
              </svg>
              <span dir="ltr" className="tracking-wide font-mono font-bold underline decoration-[#229ED9]/40 group-hover:decoration-[#229ED9]">
                @knowledgeocean123_bot
              </span>
            </a>
          </div>

          <div className="text-[11px] opacity-60 font-medium pt-1">
            Knowledge Ocean v1.0 • Canonical Architecture • Multi-Source Scholarly Retrieval
          </div>
        </footer>
      </div>
    `;
  }

  // Mount App
  const rootElement = document.getElementById("root");
  if (rootElement && typeof ReactDOM !== "undefined") {
    ReactDOM.createRoot(rootElement).render(React.createElement(App));
  }
})();
