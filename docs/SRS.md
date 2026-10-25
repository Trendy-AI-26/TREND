# TRENDY AI — Software Requirements Specification (SRS)

**الإصدار:** 1.1
**حالة الوثيقة:** متطلبات المشروع وخطة الإصدارات
**نطاق الوثيقة:** MVP والمراحل المخططة حتى Sprint 5

## 1. مقدمة

TRENDY AI هو استوديو عربي لإدارة العلامات التجارية وإنشاء صور تسويقية مناسبة لمنصات التواصل الاجتماعي. يحفظ النظام هوية كل Brand، ويحوّل إجابات المستخدم إلى brief منظم، ثم يبني الخادم prompt مناسبًا لمزود الذكاء الاصطناعي ويخزن النتيجة في سجل العلامة.

هذه وثيقة SRS مختصرة. توضح **ما الذي يجب أن يفعله النظام** و**القيود الرئيسية** و**خطة التنفيذ**، دون الدخول في تفاصيل كل ملف برمجي.

## 2. المشكلة

أصحاب المشاريع الصغيرة وصناع المحتوى يعرفون الرسالة التي يريدون إيصالها، لكنهم غالبًا لا يملكون مصممًا أو خبرة في كتابة prompts. استخدام prompt مفتوح واحد ينتج صورًا غير ثابتة، وقد لا يحافظ على هوية العلامة أو لا يناسب أبعاد المنصة المطلوبة.

## 3. الحل المقترح

يوفر TRENDY AI سير عمل بسيطًا:

1. يسجل المستخدم الدخول وينشئ Brand أو يختار Brand موجودة.
2. يحفظ المستخدم Brand Kit مثل الاسم والألوان والشعار والجمهور والنبرة.
3. يجيب المستخدم عن أسئلة حملة قصيرة بدل كتابة prompt تقني طويل.
4. يعرض النظام Preview Brief قبل التوليد.
5. يختار المستخدم المنصة، مزود الذكاء الاصطناعي، طريقة الدفع أو استخدام المفتاح، وطريقة الشعار.
6. يبني الخادم prompt النهائي ويرسل الطلب إلى المزود.
7. يحفظ النظام الصورة وحالة التوليد في History.

الهدف هو أن تبدو الصورة وكأنها جزء من العلامة، وليس كصورة عامة منفصلة عن هوية العميل.

## 4. الجمهور المستهدف

### الجمهور الأساسي

- أصحاب المشاريع الصغيرة والمتاجر المحلية.
- صناع المحتوى والمسوقون.
- العلامات العربية التي تحتاج منشورات اجتماعية متكررة.
- وكالات التسويق التي تدير أكثر من Brand.

### القطاعات المحتملة

العطور، الأزياء والعبايات، مستحضرات التجميل، المطاعم، الضيافة، التجزئة، المنتجات المحلية، والخدمات المحلية.

### المستخدم الإداري

مشغل النظام أو Admin يحتاج إلى رؤية إحصاءات عامة وقائمة العلامات لأغراض المتابعة، دون الوصول إلى API keys أو الأسرار.

## 5. نطاق المشروع

### داخل النطاق الأساسي

- تسجيل الدخول وإدارة الحساب.
- إدارة عدة علامات تجارية.
- Brand Kit لكل علامة.
- إنشاء structured campaign brief.
- Preview Brief قبل التوليد.
- توليد الصور عبر OpenAI أو Gemini أو مزود مدعوم.
- اختيار platform preset والأبعاد ونمط الشعار.
- تخزين الصور وسجل التوليد.
- إدارة API keys بشكل آمن.
- دعم أساسيات العربية والإنجليزية وRTL.
- Google Trends اختيارية ضمن Sprint 3، إذا توفر مزود مناسب.
- اختبارات regression للوظائف الأساسية.

### نطاق Sprint 4 التجاري

- اختيار واضح بين **استخدام API key الخاص بالمستخدم (BYOK)** أو **Managed Generation عبر اشتراك TRENDY AI**.
- خطط واشتراكات بسيطة.
- رصيد أو عدد توليدات حسب الخطة.
- تسجيل استهلاك التوليد ومصدر التكلفة.
- ربط بوابة دفع بطريقة منفصلة عن منطق التوليد.

### نطاق Sprint 5 الاختياري

- إنشاء Carousel يحتوي على أكثر من صورة من brief واحد.
- الحفاظ على نفس الهوية البصرية بين صور الكاروسل.
- ترتيب الصور وتحديد عددها وتنزيلها كمجموعة.
- لا ينفذ Carousel إلا إذا سمح وقت Sprint 5 بعد تثبيت المتطلبات الأساسية والدفع.

### خارج النطاق أو مؤجل

- النشر التلقائي على Instagram أو TikTok.
- جدولة المنشورات.
- تحرير الصور المتقدم.
- التعاون الكامل بين أعضاء الفريق.
- فواتير ضريبية معقدة أو نظام محاسبي كامل.
- ضمان أن كل مزود يقدم حصة مجانية لتوليد الصور.

## 6. نموذج العمل والدفع

يجب أن يختار المستخدم بوضوح طريقة استخدام الخدمة قبل التوليد أو عند إعداد الحساب.

| الخيار | ماذا يختار المستخدم؟ | من يدفع لمزود الذكاء الاصطناعي؟ | ماذا تدير TRENDY AI؟ |
|---|---|---|---|
| **BYOK** | يربط API key الخاص به | المستخدم يدفع للمزود مباشرة | مساحة العمل، Brand Kit، إدارة brief، والتوليد عبر مفتاح المستخدم |
| **Managed Generation** | يختار اشتراك أو خطة TRENDY AI | TRENDY AI تدفع للمزود | الاشتراك، الرصيد، الاستخدام، والتوليد المدَار |

### متطلبات الدفع المبسطة

- يعرض النظام الخيارين بوضوح قبل التوليد.
- لا يطلب النظام بطاقة دفع عند اختيار BYOK، إلا إذا كانت هناك رسوم اشتراك مستقلة على المنتج.
- عند اختيار Managed Generation، يجب أن تكون الخطة وحالة الاشتراك والرصيد واضحة.
- يجب أن يمنع النظام التوليد المدَار إذا انتهى الرصيد أو انتهت صلاحية الاشتراك.
- لا يجب أن يتغير prompt أو Brand Kit بسبب طريقة الدفع.
- بوابة الدفع تعيد نتيجة نجاح أو فشل فقط، بينما يخزن backend حالة الاشتراك والاستخدام.
- لا تحفظ TRENDY AI بيانات البطاقة البنكية؛ يتولى payment provider هذه البيانات.

## 7. التدفق الرئيسي للمستخدم

```text
تسجيل الدخول
  → اختيار أو إنشاء Brand
  → إكمال Brand Kit
  → فتح Generate
  → تعبئة Campaign Brief
  → مراجعة Preview Brief
  → اختيار Platform / Provider / Logo Mode
  → اختيار BYOK أو Managed Generation
  → التحقق من المفتاح أو الرصيد
  → إرسال طلب التوليد
  → عرض الصورة
  → حفظها في History وتنزيلها
```

### تدفقات بديلة مهمة

- إذا لم يكتمل Brand Kit، يظهر للمستخدم ما ينقصه بدل فشل غامض.
- إذا فشل Preview، تظهر رسالة خطأ وزر Retry دون إنشاء بطاقة ثانية.
- إذا تغير brief، يتم تحديث نفس المعاينة ويرسل النظام طلبًا جديدًا للبيانات الجديدة فقط.
- إذا فشل مزود الصور، تحفظ حالة الفشل ولا تضيع بيانات الطلب.
- إذا لم توجد حصة أو صلاحية للمفتاح، تظهر رسالة توضح أن المشكلة في provider أو quota.
- إذا انتهى رصيد Managed Generation، يقترح النظام تغيير الخطة أو استخدام BYOK إذا كان متاحًا.
- إذا اختار المستخدم Carousel، ينشئ النظام عناصر مرتبطة بنفس campaign وليس طلبات منفصلة بلا سياق.

## 8. المتطلبات الوظيفية Functional Requirements

### الحساب والعلامات

- **FR-01:** يجب أن يستطيع المستخدم تسجيل الدخول والخروج.
- **FR-02:** يجب أن يستطيع المستخدم إنشاء Brand وتعديلها وحذفها.
- **FR-03:** يجب أن يستطيع المستخدم إدارة أكثر من Brand مع فصل بيانات كل Brand.
- **FR-04:** يجب أن يمنع النظام المستخدم من الوصول إلى Brand لا يملكها.

### Brand Kit

- **FR-05:** يجب أن يستطيع المستخدم حفظ اسم العلامة، الشعار، الألوان، الجمهور، النبرة، والكلمات أو الأساليب التي يجب تجنبها.
- **FR-06:** يجب أن يعرض النظام حالة اكتمال Brand Kit بوضوح.
- **FR-07:** يجب أن يستخدم النظام Brand Kit الصحيح عند بناء prompt لكل Brand.

### Brief وPreview

- **FR-08:** يجب أن يجمع النظام campaign goal وcontent type وtarget audience وcore idea وvoice tone وoptional notes.
- **FR-09:** يجب أن يتحقق النظام من صحة brief قبل التوليد.
- **FR-10:** يجب أن يعرض Preview Brief واحدًا فقط.
- **FR-11:** يجب أن يدعم Preview حالات loading وsuccess وerror وretry.
- **FR-12:** يجب أن يرسل النظام payload منظمًا إلى endpoint المعاينة، وليس prompt النهائي الطويل من المتصفح.
- **FR-13:** يجب أن يرسل النظام طلبًا جديدًا عند تغيير brief، وألا يكرر الطلب عند بقاء brief وplatform وBrand كما هي.

### التوليد والسجل

- **FR-14:** يجب أن يستطيع المستخدم اختيار platform preset ومزود الصور وطريقة الشعار.
- **FR-15:** يجب أن يبني الخادم prompt النهائي اعتمادًا على brief وBrand Kit والمنصة واللغة والـtrend المختار إن وجد.
- **FR-16:** يجب أن يخزن النظام نتيجة التوليد وحالتها ومزودها وطريقة الدفع داخل History للعلامة الصحيحة.
- **FR-17:** يجب أن يستطيع المستخدم عرض الصورة وتنزيلها وحذف سجلها وفق الصلاحيات.
- **FR-18:** يجب أن يحافظ Carousel على brief وBrand Kit والسياق البصري المشترك بين جميع الصور.

### مفاتيح المزودين وBYOK

- **FR-19:** يجب أن يستطيع المستخدم إضافة مفتاح OpenAI أو Gemini أو مزود مدعوم.
- **FR-20:** يجب أن يستطيع المستخدم التحقق من المفتاح وتفعيله وحذفه.
- **FR-21:** يجب ألا يعيد النظام API key إلى المتصفح أو إلى response.
- **FR-22:** يجب أن يظهر للمستخدم provider وحالة المفتاح، وليس قيمة المفتاح نفسها.
- **FR-23:** يجب أن يستطيع المستخدم اختيار BYOK أو Managed Generation قبل التوليد.

### Billing وManaged Credits — Sprint 4

- **FR-24:** يجب أن يستطيع المستخدم اختيار خطة Managed Generation والاطلاع على حدودها.
- **FR-25:** يجب أن يسجل النظام subscription status وplan وcredits balance وrenewal date عند توفرها.
- **FR-26:** يجب أن يخصم النظام رصيدًا أو يسجل استخدامًا عند التوليد المدَار فقط.
- **FR-27:** يجب ألا يخصم النظام رصيد TRENDY AI عند استخدام BYOK، مع تسجيل العملية لأغراض المتابعة.
- **FR-28:** يجب أن يعالج النظام نجاح وفشل وإلغاء عملية الدفع دون كشف بيانات البطاقة.

### اللغة وGoogle Trends — Sprint 3

- **FR-29:** يجب أن يدعم النظام أساسيات العربية والإنجليزية، مع الحفاظ على النص الذي أدخله المستخدم.
- **FR-30:** يجب أن تكون Google Trends اختيارية، وألا تدخل في brief إلا بعد اختيار المستخدم صراحة.
- **FR-31:** يجب أن يتحقق الخادم من region وtrend id ووقت التحديث قبل إدخالها في prompt.
- **FR-32:** يجب أن يستمر التوليد عند تعطل مزود Trends أو إيقاف الميزة.

### Caption وCarousel — Sprint 3 و5

- **FR-33:** يمكن إضافة caption بعد نجاح الصورة دون إعادة توليدها.
- **FR-34:** يمكن للمستخدم تحديد عدد صور Carousel، بحد أعلى يحدده النظام.
- **FR-35:** يجب أن تعرض الواجهة صور Carousel بالترتيب مع إمكانية إعادة الترتيب أو التنزيل كمجموعة عند تنفيذ الميزة.

## 9. المتطلبات غير الوظيفية Non-Functional Requirements

- **NFR-01 — الأمان:** المصادقة مطلوبة، وكل Brand وGeneration وBilling record محمي بملكية المستخدم.
- **NFR-02 — سرية المفاتيح:** تخزن مفاتيح المزودين في الخادم أو Supabase Vault، ولا تظهر في frontend أو logs.
- **NFR-03 — الدفع الآمن:** لا تخزن TRENDY AI بيانات البطاقة، وتتعامل مع payment provider عبر server-side webhook أو API آمن.
- **NFR-04 — الاعتمادية:** فشل مزود خارجي يظهر كخطأ مفهوم ولا يؤدي إلى فقدان brief أو سجل التوليد.
- **NFR-05 — منع التكرار:** لا ينشئ React أو API Preview أو webhook مكررًا لنفس العملية.
- **NFR-06 — Idempotency:** يجب أن يحمل إنشاء الدفع والتوليد معرفًا فريدًا يمنع خصمًا أو توليدًا مزدوجًا عند إعادة الطلب.
- **NFR-07 — الأداء:** تظهر حالات loading وerror بوضوح، وتستخدم Trends cache بدل طلب المزود لكل مستخدم.
- **NFR-08 — قابلية التوسع:** تكون AI providers وpayment providers خلف adapters مستقلة.
- **NFR-09 — سهولة الاستخدام:** الأسئلة قصيرة وواضحة، وخيار BYOK أو Managed Generation مفهوم للمستخدم غير التقني.
- **NFR-10 — دعم العربية:** يحافظ النظام على UTF-8 والنص العربي والمختلط دون corruption أو عكس غير متوقع.
- **NFR-11 — الاستجابة:** الواجهات الأساسية قابلة للاستخدام على الهاتف وسطح المكتب.
- **NFR-12 — الاختبار:** يجب أن تمر اختبارات backend وfrontend وcontract قبل الدمج.
- **NFR-13 — الخصوصية:** لا يتم تخزين الأسرار داخل Git، ولا يتم كشف بيانات Brand أو Billing لمستخدم آخر.
- **NFR-14 — المراقبة:** تحفظ حالات النجاح والفشل وprovider وmodel وbilling mode ووقت الطلب دون تسجيل الأسرار.
- **NFR-15 — الاتساق البصري:** صور Carousel تستخدم نفس Brand Kit والسياق البصري لتقليل اختلاف الأسلوب بين الشرائح.

## 10. المعمارية والتفاصيل التقنية

### الطبقات

```text
Next.js / React UI
  → Next.js API routes أو API client
  → FastAPI REST API
  → Services: validation, prompt composer, billing, provider adapters
  → Supabase Auth / Postgres / Storage / Vault
  → AI provider أو Payment provider
```

### مسؤوليات الواجهة

- عرض Brand وBrand Kit وHistory.
- جمع structured brief فقط.
- عرض loading/error/success states.
- اختيار المنصة وطريقة الدفع والمزود.
- عدم بناء prompt النهائي أو تخزين الأسرار.

### مسؤوليات FastAPI

- التحقق من الهوية والملكية.
- التحقق من Pydantic schemas والـenums والحدود.
- تحميل Brand Kit الصحيح.
- بناء prompt النهائي في `prompt_composer`.
- اختيار provider adapter.
- التحقق من BYOK أو subscription/credits قبل التوليد.
- حفظ generation status مثل `pending`, `succeeded`, `failed`.
- إرجاع رسائل خطأ آمنة وقابلة للعرض.

### البيانات الأساسية

| الكيان | أهم البيانات |
|---|---|
| User/Profile | user id، email، إعدادات اللغة |
| Brand | owner id، name، logo، timestamps |
| BrandKit | tone، audience، colors، avoid words، completion status |
| ProviderKey | brand id، provider، Vault secret id، hint، active/valid status |
| Generation | brand id، brief snapshot، provider، model، billing mode، status، image path، error metadata |
| Subscription | user/workspace id، plan، status، renewal date، provider customer id |
| CreditLedger | owner id، amount، type، generation id، idempotency key |
| Carousel | generation group id، count، order، shared brief/context |

### واجهات API الرئيسية

| Endpoint | الغرض |
|---|---|
| `GET/POST /brands` | عرض وإنشاء العلامات |
| `GET/PATCH/DELETE /brands/{brand_id}` | إدارة Brand واحدة |
| `GET/PUT /brands/{brand_id}/kit` | قراءة وتحديث Brand Kit |
| `POST /brands/{brand_id}/preview-brief` | إنشاء Preview Brief |
| `GET/POST/DELETE /brands/{brand_id}/keys` | إدارة provider keys |
| `POST /brands/{brand_id}/generate` | توليد صورة أو مجموعة توليد |
| `GET /brands/{brand_id}/generations` | عرض History |
| `GET /trends/regions` | المناطق المتاحة في Trends |
| `GET /trends` | قائمة Trends المخبأة |
| `POST /brands/{brand_id}/generations/{id}/caption` | توليد Caption بعد الصورة |
| `GET /billing/plans` | عرض خطط Managed Generation |
| `GET /billing/me` | عرض الاشتراك والرصيد |
| `POST /billing/checkout` | إنشاء عملية دفع عبر provider |
| `POST /billing/webhook` | استقبال نتيجة الدفع بأمان |

### قواعد API العامة

- كل endpoint محمي بالمصادقة عند الحاجة.
- كل endpoint يطبق ownership check على `brand_id` و`generation_id`.
- payloads منظمة ومحددة عبر Pydantic وTypeScript types.
- الأخطاء ترجع `code` و`message` و`request_id` دون أسرار.
- العمليات القابلة لإعادة الإرسال تستخدم idempotency key.

## 11. التقنيات المستخدمة

| الطبقة | التقنية |
|---|---|
| Frontend | Next.js 14، React، TypeScript، Tailwind CSS |
| Backend | Python، FastAPI، Pydantic |
| Authentication | Supabase Auth |
| Database | Supabase Postgres مع Row Level Security |
| Storage | Supabase Storage للصور والشعارات |
| Secrets | Supabase Vault أو تخزين خادمي آمن |
| AI providers | OpenAI وGoogle Gemini عبر provider adapters |
| Trends | Provider adapter مع cache وfeature flag |
| Billing | Payment provider عبر server-side API وwebhook، دون تخزين بيانات البطاقة |
| Testing | Pytest للـbackend وVitest/Testing Library للـfrontend |
| التشغيل | Docker وDocker Compose |
| إدارة الكود | Git وGitHub |

## 12. خطة الـSprints والـBacklog

### Sprint 0 — Foundation and Product Setup

إعداد المشروع، الهوية، المصادقة، قاعدة البيانات، التخزين، Docker، وبنية API الأساسية.

### Sprint 1 — Brand Workspace and Brand Kit

إدارة العلامات، رفع الشعار، Brand Kit، الألوان، النبرة، الجمهور، وملخص الهوية.

### Sprint 2 — Structured Generation Pipeline

تعريف brief contract، questionnaire، Preview Brief، prompt composer، provider keys، توليد الصور، watermark، التخزين، وHistory.

### Sprint 3 — Arabic, Google Trends, Captions, and Quality

- إغلاق اختبارات Preview Brief وregression.
- دعم العربية والإنجليزية وRTL.
- إضافة Google Trends اختيارية مع regions وcache وfeature flag.
- إدخال trend المختار في brief وprompt فقط بعد موافقة المستخدم.
- إضافة Caption بعد نجاح الصورة.
- ضمان استمرار التوليد عند تعطل Trends.

### Sprint 4 — Billing and Managed Credits

- إضافة اختيار واضح بين BYOK وManaged Generation.
- إضافة plans بسيطة مثل Trial وBasic وPro أو ما يقرره المنتج.
- إضافة subscription status.
- إضافة credit balance وcredit ledger.
- إضافة checkout وwebhook عبر payment provider.
- ربط خصم الرصيد بالتوليد المدَار فقط.
- إضافة idempotency ومنع الخصم المكرر.
- إضافة صفحة بسيطة لعرض الخطة والرصيد وحالة الدفع.

### Sprint 5 — Carousel and Commercial Polish

- تنفيذ Carousel اختياري إذا سمح الوقت بعد إغلاق Sprint 4.
- تحديد عدد الصور وإنشاء مجموعة مرتبطة بنفس brief.
- الحفاظ على Brand Kit والسياق البصري بين الصور.
- عرض الصور بالترتيب وإعادة ترتيبها عند الحاجة.
- تنزيل الصور كملفات منفصلة أو ZIP عند توفر الوقت.
- تحسين History، رسائل الدفع، وتجربة المستخدم responsive.
- تنفيذ end-to-end regression قبل الإصدار.

### عناوين Backlog الرئيسية

- Account and Authentication.
- Multi-brand Workspace.
- Brand Kit.
- Provider Keys and BYOK.
- Structured Generation Brief.
- Preview Brief and Regression Tests.
- Image Generation and Provider Adapters.
- Generation History.
- Arabic/English and RTL.
- Google Trends Provider and Cache.
- SEO Caption Generation.
- Billing and Managed Credits.
- Payment Checkout and Webhooks.
- Carousel Generation.
- Admin Monitoring and Release QA.

## 13. User Stories

- **US-01:** كمستخدم، أريد تسجيل الدخول حتى أستطيع الوصول إلى علاماتي.
- **US-02:** كصاحب مشروع، أريد إنشاء Brand وحفظ هويتها حتى لا أعيد كتابة المعلومات في كل حملة.
- **US-03:** كمستخدم، أريد الإجابة عن أسئلة بسيطة بدل كتابة prompt طويل.
- **US-04:** كمستخدم، أريد رؤية Preview Brief قبل التوليد حتى أراجع ما سيرسله النظام.
- **US-05:** كمستخدم، أريد تعديل brief وإعادة المعاينة دون ظهور نسخة ثانية.
- **US-06:** كمستخدم، أريد اختيار استخدام API key الخاص بي أو الاشتراك في Managed Generation.
- **US-07:** كمستخدم BYOK، أريد أن يبقى مفتاحي مخفيًا وأن أرى حالته فقط.
- **US-08:** كمستخدم Managed Generation، أريد معرفة خطتي ورصيدي قبل التوليد.
- **US-09:** كمستخدم، أريد اختيار المنصة والشعار حتى تناسب الصورة مكان استخدامها.
- **US-10:** كمستخدم، أريد رؤية الصورة في History وتنزيلها لاحقًا.
- **US-11:** كمستخدم عربي، أريد استخدام الواجهة والنص العربي دون مشاكل RTL.
- **US-12:** كمسوق، أريد اختيار Google Trend اختياري حتى أضيفه للحملة فقط عندما يكون مناسبًا.
- **US-13:** كمسوق، أريد توليد Caption بعد الصورة وتعديله أو نسخه.
- **US-14:** كمسوق، أريد إنشاء Carousel من عدة صور متناسقة لنفس الحملة.
- **US-15:** كـAdmin، أريد رؤية إحصاءات عامة دون رؤية المفاتيح أو بيانات الدفع الحساسة.

## 14. افتراضات وقرارات

- يحتاج المستخدم إلى حساب مصادق عليه.
- لا يبدأ التوليد قبل التحقق من ownership وBrand Kit والـprovider أو الاشتراك.
- قد يفرض مزود الذكاء الاصطناعي quotas أو رسومًا مستقلة.
- صلاحية API key لا تعني أن حصة توليد الصور مجانية أو متاحة.
- الدفع لا يغيّر prompt أو Brand Kit أو نتيجة التحقق من الملكية.
- المستخدم يختار BYOK أو Managed Generation بوضوح، ولا يبدل النظام الطريقة تلقائيًا.
- Google Trends لا يمنع التوليد إذا كان provider غير متاح.
- Carousel ميزة مشروطة بالوقت، ولا تؤخر إطلاق المسار الأساسي أو Billing.
- لا يتم إرسال prompt النهائي الطويل من المتصفح؛ الخادم هو المسؤول عن تركيبه.

## 15. معايير النجاح

يعتبر الإصدار الأساسي ناجحًا عندما يستطيع المستخدم تسجيل الدخول، إنشاء Brand، إكمال Brand Kit، تعبئة brief، مراجعة Preview واحد، اختيار BYOK أو Managed Generation، توليد صورة بمزود صالح، حفظ الصورة في History، ثم تنزيلها دون كشف المفاتيح أو بيانات Brand لمستخدم آخر.

ويعتبر Sprint 3 ناجحًا عند عمل العربية وGoogle Trends الاختيارية وCaption دون كسر مسار Sprint 2. ويعتبر Sprint 4 ناجحًا عند معرفة المستخدم للخطة والرصيد وطريقة الدفع، ومعالجة الدفع والخصم دون تكرار أو كشف بيانات حساسة. ويعتبر Sprint 5 ناجحًا عند إنشاء Carousel متناسق إذا تم اعتماده ضمن وقت السبرنت.

## 16. جدول الربط بين User Stories والمتطلبات

| User Story | Functional Requirements | Non-Functional Requirements |
|---|---|---|
| US-01 تسجيل الدخول | FR-01 | NFR-01، NFR-13 |
| US-02 إدارة Brand وBrand Kit | FR-02، FR-03، FR-05، FR-06، FR-07 | NFR-01، NFR-09 |
| US-03 تعبئة brief منظم | FR-08، FR-09 | NFR-07، NFR-10 |
| US-04 مراجعة Preview | FR-10، FR-11، FR-12 | NFR-04، NFR-05 |
| US-05 تعديل brief وRetry | FR-11، FR-13 | NFR-04، NFR-06 |
| US-06 اختيار BYOK أو Managed | FR-23، FR-24 | NFR-03، NFR-09 |
| US-07 حماية API key | FR-19، FR-20، FR-21، FR-22 | NFR-01، NFR-02، NFR-13 |
| US-08 معرفة الخطة والرصيد | FR-24، FR-25، FR-26 | NFR-03، NFR-06، NFR-14 |
| US-09 اختيار المنصة والشعار | FR-14، FR-15 | NFR-08، NFR-11 |
| US-10 History والتنزيل | FR-16، FR-17 | NFR-01، NFR-04 |
| US-11 العربية وRTL | FR-29 | NFR-09، NFR-10، NFR-11 |
| US-12 Google Trends | FR-30، FR-31، FR-32 | NFR-04، NFR-07، NFR-08 |
| US-13 Caption | FR-33 | NFR-03، NFR-10 |
| US-14 Carousel | FR-18، FR-34، FR-35 | NFR-15، NFR-07 |
| US-15 Admin monitoring | إحصاءات Admin وقراءة الحالة | NFR-01، NFR-02، NFR-03، NFR-14 |

## 17. مراجع تقنية مختصرة

[1]: https://nextjs.org/docs "Next.js Documentation"

[2]: https://fastapi.tiangolo.com/ "FastAPI Documentation"

[3]: https://supabase.com/docs "Supabase Documentation"

[4]: https://ai.google.dev/gemini-api/docs "Google Gemini API Documentation"
