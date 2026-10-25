# TRENDY AI — Sprint 3 Backlog

**Sprint goal:** إصلاح تجربة Preview Brief، ثم إضافة توليد صور واعٍ بالترند، ودعم عربي/إنجليزي حقيقي، وتوليد كابشن SEO بعد نجاح الصورة.

**Suggested duration:** 2 أسابيع، ويُعدّل حسب عدد أعضاء الفريق.

**Execution rule:** لا نبدأ التكاملات الجديدة قبل إغلاق مهمة Preview Brief P0 والتأكد من عدم كسر مسار Sprint 2.

## 1. Sprint map

| Phase | Focus | Main owner | Depends on |
| --- | --- | --- | --- |
| Phase 0 | Discovery and contract alignment | FE + BE | None |
| Phase 1 | Preview Brief carry-over fix | FE + BE support | Phase 0 |
| Phase 2 | Language and RTL foundation | FE + BE | Phase 0 |
| Phase 3 | Trends provider and selection flow | BE first, then FE | Phase 2 contracts |
| Phase 4 | Caption generation | BE first, then FE | Language contract; successful generation |
| Phase 5 | Integration, QA, and release | FE + BE + QA | All P0/P1 tasks |

## 2. Board-ready task list

| ID | Type | Title | Owner | Priority | Estimate | Depends on |
| --- | --- | --- | --- | --- | --- | --- |
| S3-00 | Spike | Audit Sprint 2 contracts and render tree | FE + BE | P0 | 0.5 day | — |
| S3-01 | Bug | Fix duplicated Preview Brief rendering | FE | P0 | 1 day | S3-00 |
| S3-02 | Test | Add Preview Brief regression coverage | FE + BE | P0 | 0.5 day | S3-01 |
| S3-03 | Contract | Define language enum and localization contract | BE | P0 | 0.5 day | S3-00 |
| S3-04 | Feature | Add Arabic/English selector and RTL shell | FE | P0 | 1.5 days | S3-03 |
| S3-05 | Feature | Pass language through brief, preview, and generation | FE + BE | P0 | 1 day | S3-03, S3-04 |
| S3-06 | Test | Validate Arabic, English, RTL, and mixed-script input | FE + BE | P0 | 1 day | S3-05 |
| S3-07 | Spike | Verify Trends provider, access, terms, quota, and Arabic coverage | BE | P1 | 1 day | S3-00 |
| S3-08 | Contract | Create normalized Trends provider adapter | BE | P1 | 1 day | S3-07 |
| S3-09 | API | Implement regions and cached trends endpoints | BE | P1 | 1.5 days | S3-08 |
| S3-10 | Feature | Build optional Trends selector UI | FE | P1 | 1.5 days | S3-09 |
| S3-11 | Feature | Add selected trend to structured brief and preview | FE + BE | P1 | 1 day | S3-05, S3-10 |
| S3-12 | Test | Test Trends failure tolerance and prompt inclusion | FE + BE | P1 | 1 day | S3-11 |
| S3-13 | Contract | Define caption request and structured response | BE | P1 | 0.5 day | S3-03, S3-05 |
| S3-14 | API | Implement post-generation caption endpoint | BE | P1 | 1.5 days | S3-13 |
| S3-15 | Feature | Build caption panel, edit, copy, and regenerate actions | FE | P1 | 1.5 days | S3-14 |
| S3-16 | Data | Persist caption history and generation context | BE | P2 | 1 day | S3-14 |
| S3-17 | QA | Run end-to-end regression and responsive verification | FE + BE + QA | P0 | 1 day | S3-02, S3-06, S3-12, S3-15 |
| S3-18 | Release | Update docs, environment variables, monitoring, and rollout notes | FE + BE | P0 | 0.5 day | S3-17 |

## 3. Detailed task specifications

### Phase 0 — Discovery and contracts

#### S3-00 — Audit Sprint 2 contracts and render tree

**Owner:** Frontend + Backend. **Priority:** P0. **Estimate:** 0.5 day.

افحص `generation-brief-form`, `brief-creative-preview`, الحاوية الأب، hook الخاص بـ preview، ومسار `/preview-brief`. سجّل أين يتم تركيب المكوّن، كم مرة يتم استدعاء الطلب، وما إذا كان هناك اختلاف بين desktop وmobile. راجع أيضًا عقد `GenerationBrief` و`build_generation_prompt` قبل إضافة الحقول الجديدة.

**Acceptance criteria:** يوجد توثيق قصير لمسار render وrequest؛ تم تحديد المكوّن الأب المسؤول عن المعاينة؛ تم تحديد العقد التي تحتاج تعديلًا؛ ولا يتم اقتراح إخفاء النسخة الثانية باستخدام CSS كحل.

### Phase 1 — Preview Brief carry-over

#### S3-01 — Fix duplicated Preview Brief rendering

**Owner:** Frontend. **Priority:** P0. **Estimate:** 1 day. **Dependency:** S3-00.

اجعل هناك instance واحدًا canonical من `BriefCreativePreview` داخل review step. انقل placement والـ visibility إلى parent واحد، وأزل أي تركيب مكرر في child أو wrapper آخر. استخدم stable query key مبنيًا على brand، brief، وplatform. عند تغيير البيانات، حدّث نفس المكوّن بدل إضافة card جديد.

**Acceptance criteria:** يظهر عنوان Preview Brief مرة واحدة فقط؛ يظهر card واحد في desktop وmobile؛ تغيير إجابة لا يضيف card جديدًا؛ retry يعيد استخدام نفس الحالة؛ ولا يوجد طلب مكرر ناتج عن mount غير ضروري.

#### S3-02 — Add Preview Brief regression coverage

**Owner:** Frontend + Backend. **Priority:** P0. **Estimate:** 0.5 day. **Dependency:** S3-01.

أضف اختبار render يثبت عدد عناوين/مكوّنات Preview Brief، واختبارًا لمسار retry وتغيير brief. أضف تحققًا من endpoint يمنع regression في payload والملكية، ثم شغّل اختبارات preview الحالية.

**Acceptance criteria:** يفشل الاختبار إذا ظهر Preview Brief مرتين؛ تمر حالات loading/error/success؛ وتبقى اختبارات Sprint 2 الحالية ناجحة.

### Phase 2 — Language and RTL

#### S3-03 — Define language enum and localization contract

**Owner:** Backend. **Priority:** P0. **Estimate:** 0.5 day.

عرّف `language` بقيمتي `ar` و`en` على مستوى schema/model/request validation. حدّد default واضحًا للمنتج، وقرّر هل `ui_locale` منفصل عن `text_language` في هذه المرحلة. يجب أن يضيف server تعليمات اللغة إلى prompt دون ترجمة `core_idea` أو النص الذي أدخله المستخدم من تلقاء نفسه.

**Acceptance criteria:** القيم غير المسموحة تُرفض برسالة واضحة؛ العقد موحد بين preview وgeneration وcaption؛ الحقل موثق في TypeScript/Pydantic؛ والـ prompt composer يطبق instruction واحدة متسقة.

#### S3-04 — Add Arabic/English selector and RTL shell

**Owner:** Frontend. **Priority:** P0. **Estimate:** 1.5 days. **Dependency:** S3-03.

أضف Language Selection في بداية أو review step من نموذج التوليد. اعرض Arabic وEnglish بطريقة واضحة، وفعّل `dir="rtl"` عند العربية مع الحفاظ على اتجاه الأرقام والأكواد وحقول mixed text. ترجم labels وvalidation وempty/error states الأساسية دون نسخ مكوّنات الواجهة.

**Acceptance criteria:** يبدّل المستخدم بين AR وEN دون فقدان بيانات questionnaire؛ تعمل الواجهة على mobile وdesktop؛ focus order وkeyboard navigation صحيحان؛ لا تنقلب الأيقونات أو النصوص المختلطة بشكل غير مفهوم؛ وتظهر اللغة المختارة في review summary.

#### S3-05 — Pass language through brief, preview, and generation

**Owner:** Frontend + Backend. **Priority:** P0. **Estimate:** 1 day. **Dependencies:** S3-03, S3-04.

أضف `language` إلى structured brief، واجعل frontend يرسل البيانات المنظمة فقط. حدّث preview وprompt composer وgeneration request حتى يستخدموا القيمة نفسها. يجب أن يصل التوجيه إلى image provider server-side، مع الحفاظ على exact visible text عندما يطلبه المستخدم.

**Acceptance criteria:** request واحد متسق يحمل `ar` أو `en`؛ preview يعكس اللغة؛ image prompt يحتوي instruction اللغة؛ النص الأصلي محفوظ حرفيًا؛ ولا يتم بناء final prompt الطويل في المتصفح.

#### S3-06 — Validate Arabic, English, RTL, and mixed-script input

**Owner:** Frontend + Backend. **Priority:** P0. **Estimate:** 1 day. **Dependency:** S3-05.

اكتب اختبارات contract وUI للنص العربي والإنجليزي والمختلط، punctuation، الأرقام، والـ hashtags. تحقق من عدم حدوث Unicode corruption أو reversal غير متوقع، ومن أن الـ validation messages مترجمة أو مرتبطة بالـ locale الصحيح.

**Acceptance criteria:** تمر حالات Arabic وEnglish وmixed script؛ يحافظ النظام على `core_idea` كما أدخله المستخدم؛ وتُلتقط أي مشكلة RTL في الاختبار أو checklist المرئي قبل الدمج.

### Phase 3 — Google Trends

#### S3-07 — Verify Trends provider, access, terms, quota, and Arabic coverage

**Owner:** Backend. **Priority:** P1. **Estimate:** 1 day.

تحقق من مزوّد حي قابل للاستخدام، access credentials، شروط الاستخدام، quotas، response shape، ودعم المناطق العربية. لا تعتمد على مكتبة غير مستقرة كمصدر الإنتاج الوحيد. إذا لم يتوفر provider جاهز، أبقِ adapter خلف feature flag مع fallback واضح إلى manual trend input أو تعطيل Trends.

**Acceptance criteria:** قرار موثق بمزوّد أساسي وfallback؛ credentials لا تدخل git؛ تم توثيق quota وtimeout وcache policy؛ ويستطيع المستخدم توليد صورة مع Trends disabled أو provider unavailable.

#### S3-08 — Create normalized Trends provider adapter

**Owner:** Backend. **Priority:** P1. **Estimate:** 1 day. **Dependency:** S3-07.

أنشئ interface provider مستقلًا عن المصدر، يحوّل النتائج إلى `id`, `title`, `region_code`, `status`, `started_at`, `updated_at`, `volume_label`, `related_queries`, و`source`. طبّق validation للحجم والترميز والـ region، واعتبر كل البيانات الخارجية untrusted.

**Acceptance criteria:** يمكن تبديل provider دون تعديل frontend؛ malformed response لا يكسر التطبيق؛ النتائج لا تتجاوز limit محدد؛ ويعيد adapter حالة unavailable قابلة للعرض بدل exception غير مفهومة.

#### S3-09 — Implement regions and cached trends endpoints

**Owner:** Backend. **Priority:** P1. **Estimate:** 1.5 days. **Dependency:** S3-08.

نفّذ `GET /trends/regions` و`GET /trends?region=...&window=24h&active_only=true`. أضف cache server-side وmanual refresh support، وسجّل `updated_at`. طبّق allowlist للمناطق والنوافذ، timeout، rate limiting أو حماية مناسبة، ورسائل خطأ لا تكشف secrets.

**Acceptance criteria:** endpoint يعيد regions مترجمة أو قابلة للترجمة؛ trends endpoint يدعم loading/empty/unavailable/error semantics؛ البيانات المخبأة لا تعيد طلب provider لكل مستخدم؛ ولا يمنع فشل Trends عملية image generation.

#### S3-10 — Build optional Trends selector UI

**Owner:** Frontend. **Priority:** P1. **Estimate:** 1.5 days. **Dependency:** S3-09.

أضف toggle أو disclosure بعنوان واضح مثل “Use current trends (optional)”. بعد التفعيل، اعرض region selector، refresh، trend list، last updated، active state، وsearch/selection عند الحاجة. اعرض selected trend كـ chip مع clear وreplace، ولا تختَر trend تلقائيًا.

**Acceptance criteria:** Trends غير مفعّل افتراضيًا أو حسب قرار المنتج الموثق؛ لا يظهر trend في brief دون اختيار صريح؛ حالات loading/empty/error/unavailable مفهومة؛ clear وreplace يعملان؛ والواجهة RTL-compatible.

#### S3-11 — Add selected trend to structured brief and preview

**Owner:** Frontend + Backend. **Priority:** P1. **Estimate:** 1 day. **Dependencies:** S3-05, S3-10.

أضف selected trend object إلى brief، مع snapshot للعنوان والمنطقة والمصدر وقت التوليد. حدّث preview ليعرض trend context كمعلومة منفصلة، ثم اجعل server-side composer يضيفه فقط إذا كان موجودًا ومُتحققًا منه.

**Acceptance criteria:** لا يوجد trend field أو يكون null عند التعطيل؛ trend المختار يظهر في review؛ server يرفض region/id غير صالحين؛ prompt يحتوي trend المختار فقط؛ وإزالة trend تعيد generation إلى المسار العادي.

#### S3-12 — Test Trends failure tolerance and prompt inclusion

**Owner:** Frontend + Backend. **Priority:** P1. **Estimate:** 1 day. **Dependency:** S3-11.

غطِّ provider timeout، stale cache، malformed data، empty list، unavailable feature، clear/replace، وعدم تسريب بيانات provider. اختبر أن prompt لا يحتوي trend عند عدم الاختيار، ويحتوي snapshot الصحيح عند الاختيار.

**Acceptance criteria:** الصورة تُولد مع provider down؛ لا يتم اختيار trend صامتًا؛ لا يتم إرسال prompt من client؛ وكل حالات Trends الأساسية لها اختبار regression.

### Phase 4 — Caption generation

#### S3-13 — Define caption request and structured response

**Owner:** Backend. **Priority:** P1. **Estimate:** 0.5 day. **Dependencies:** S3-03, S3-05.

حدّد request لـ `language`, `platform`, `optional preferences`، وحدّد response يشمل `caption`, `hook`, `hashtags`, `keywords`, `trend_used`, و`language`. ضع حدودًا للطول وعدد hashtags، وتعليمات SEO طبيعية غير مبنية على keyword stuffing.

**Acceptance criteria:** response schema قابل للتحقق؛ اللغة متسقة مع generation؛ hashtags مصفوفة منفصلة؛ trend_used boolean صحيح؛ وفشل model لا يفسد سجل الصورة.

#### S3-14 — Implement post-generation caption endpoint

**Owner:** Backend. **Priority:** P1. **Estimate:** 1.5 days. **Dependency:** S3-13.

نفّذ `POST /brands/{brand_id}/generations/{generation_id}/caption`. تحقق من ownership ومن أن generation ناجح، حمّل brief/platform/brand context، استدعِ text model server-side، تحقّق من structured output، وأعد error mapping واضحًا. لا تعِد توليد الصورة إذا فشل الكابشن.

**Acceptance criteria:** لا يعمل endpoint على generation تخص brand أخرى؛ لا يعمل قبل نجاح الصورة؛ يعيد caption باللغة المختارة؛ يمكن استدعاؤه أكثر من مرة؛ timeout لا يحذف الصورة؛ وprovider secrets لا تظهر في logs أو response.

#### S3-15 — Build caption panel, edit, copy, and regenerate actions

**Owner:** Frontend. **Priority:** P1. **Estimate:** 1.5 days. **Dependency:** S3-14.

بعد نجاح الصورة، اعرض CTA مستقلًا لتوليد الكابشن. اعرض loading/error/success، الحقول القابلة للتحرير، hashtags منفصلة، copy action، regenerate action، وlanguage/trend summary. لا تعرض CTA عند generation failed أو processing.

**Acceptance criteria:** يمكن تعديل النص قبل النسخ؛ copy يعطي feedback؛ regenerate لا يغير image URL أو generation ID؛ الكابشن لا يفرض نفسه على المستخدم للنشر؛ والتجربة تعمل بالعربية والإنجليزية.

#### S3-16 — Persist caption history and generation context

**Owner:** Backend. **Priority:** P2. **Estimate:** 1 day. **Dependency:** S3-14.

أضف migration وجدول `generation_captions` إذا قرر الفريق حفظ التاريخ. خزّن language، output structured fields، model، context version، timestamps، وfailure metadata عند الحاجة. طبّق RLS/ownership واحتفظ بسnapshot trend المختار لأغراض reproducibility.

**Acceptance criteria:** regeneration ينشئ record مستقلًا أو يحدّثه حسب قرار المنتج؛ لا يمكن cross-brand access؛ يمكن معرفة أي لغة وسياق أنتجا الكابشن؛ وتبقى البيانات قابلة للحذف وفق سياسات المنتج.

### Phase 5 — QA and release

#### S3-17 — Run end-to-end regression and responsive verification

**Owner:** Frontend + Backend + QA. **Priority:** P0. **Estimate:** 1 day. **Dependencies:** S3-02, S3-06, S3-12, S3-15.

نفّذ المسارات التالية: generation بدون Trends وبدون caption؛ generation مع لغة عربية؛ generation مع English؛ generation مع trend مختار؛ provider unavailable؛ caption success؛ caption failure؛ وregenerate caption. افحص desktop/mobile وRTL.

**Acceptance criteria:** يمر المسار الأساسي القديم؛ لا يوجد Preview Brief مكرر؛ لا يمنع Trends أو caption فشل الصورة؛ لا توجد أخطاء console أو API غير معالجة؛ وتوثق نتائج الاختبار قبل release.

#### S3-18 — Update docs, environment variables, monitoring, and rollout notes

**Owner:** Frontend + Backend. **Priority:** P0. **Estimate:** 0.5 day. **Dependency:** S3-17.

حدّث Sprint 3 plan، README أو deployment notes عند الحاجة، `.env.example` دون أسرار، provider setup، feature flags، cache policy، error codes، وrunbook مختصر لتعطيل Trends أو captions إذا تعطل provider.

**Acceptance criteria:** يستطيع عضو جديد تشغيل المسار الأساسي؛ جميع environment variables موثقة؛ يوجد fallback تشغيلي؛ ووثائق البورد والكود متطابقة مع التنفيذ.

## 4. Recommended board columns

| Column | Meaning |
| --- | --- |
| Backlog | المهمة موثقة ولم تبدأ |
| Ready | الاعتماديات مكتملة وقابلة للسحب |
| In Progress | يعمل عليها شخص واحد أو فريق واضح |
| Review | الكود والاختبارات جاهزة للمراجعة |
| QA | التحقق الوظيفي والاستجابة والـ RTL |
| Done | معايير القبول والاختبارات والتوثيق مكتملة |
| Blocked | يوجد provider أو قرار أو credential يمنع الاستمرار |

## 5. Suggested ownership split

| Area | Frontend responsibility | Backend responsibility |
| --- | --- | --- |
| Preview Brief | render tree، state، responsive UI، request lifecycle | contract stability، ownership، endpoint tests |
| Language | selector، RTL، translations، mixed-script UX | enum، validation، prompt instruction، persistence |
| Trends | toggle، region/trend selection، error states، selected chip | provider adapter، cache، normalization، endpoint، validation |
| Caption | CTA، result editor، copy/regenerate، state management | endpoint، model call، structured validation، ownership، history |
| Release | visual regression، client tests، UX checklist | API tests، migrations، observability، fallback/runbook |

## 6. Out of scope for this sprint

لا يشمل Sprint 3 النشر التلقائي إلى Instagram أو أي منصة اجتماعية، ولا نظام SEO متقدم خاص بكل محرك بحث، ولا اختيار ترند تلقائيًا دون موافقة المستخدم، ولا جعل Trends شرطًا لتوليد الصورة، ولا دعم لغات إضافية خارج Arabic وEnglish، ولا إعادة كتابة `core_idea` بصمت.

## 7. Sprint exit criteria

يُغلق Sprint 3 عندما تُنجز جميع مهام P0، وتنجز مهام P1 أو تُنقل رسميًا إلى Sprint 4 مع سبب واضح. يجب أن يستطيع المستخدم إكمال المسار القديم دون Trends أو captions، واختيار اللغة العربية أو الإنجليزية، واختيار trend إقليمي اختياريًا، وتوليد caption بعد الصورة، مع بقاء كل البيانات محكومة بملكية الـ brand والـ generation.
