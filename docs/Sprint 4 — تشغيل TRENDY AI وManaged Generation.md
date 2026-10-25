# Sprint 4 — تشغيل TRENDY AI وManaged Generation

## 1. القرار المنتجّي

ينتقل TRENDY AI من نموذج **BYOK (Bring Your Own Key)** إلى نموذج **Managed Generation**:

- المستخدم لا يضيف أو يدير أي API key.
- TRENDY AI يحتفظ بمفاتيح مزوّدي الذكاء الاصطناعي في الـ backend فقط، من خلال متغيرات سرية أو Secret Manager.
- المستخدم يختار المحتوى والإعدادات فقط؛ لا يختار المزوّد ولا يرى المفتاح.
- الدفع الفعلي غير مفعّل في هذه المرحلة، لكن النظام يتصرف من الآن كمنتج اشتراكات: خطة، رصيد، استهلاك، وسجل تكلفة.
- الخطة المؤقتة المناسبة للتشغيل: **Free / Beta** برصيد مجاني محدود، مع إمكانية تغيير الرصيد من إعدادات backend بدون تعديل الواجهة.

هذا القرار صحيح للـ MVP لأنه يمنع تسريب مفاتيح المستخدمين، يقلل عدد حالات الفشل، ويجعل تكلفة كل مستخدم قابلة للقياس. لكنه ينقل مسؤولية التكلفة والأمان ومقاومة إساءة الاستخدام إلى TRENDY AI؛ لذلك لا يجوز تشغيله بلا quota وrate limiting وسجل استهلاك.

## 2. سبب عدم توليد الصورة حاليًا

المشكلة ليست بالضرورة في واجهة رفع المفتاح. الكود الحالي مبني حول BYOK بالكامل:

1. `frontend/components/generation/generator-form.tsx` يستدعي `useActiveKeys`.
2. زر التوليد يتعطل إذا لم يوجد مفتاح نشط للمزوّد المختار.
3. `backend/app/routers/generations.py` يبحث عن مفتاح نشط في `provider_keys` لكل Brand.
4. الـ API key يُقرأ من Supabase Vault، ثم يُمرر إلى OpenAI أو Gemini.
5. توليد الكابشن يستخدم نفس المسار ويحتاج إلى مفتاح نشط أيضًا.

إذًا عند عدم وجود مفتاح صحيح في Vault، أو إذا كان المفتاح غير مصرح له بتوليد الصور، أو إذا كان الموديل/الحساب لا يدعم endpoint المستخدم، لن تتولد صورة. لا يوجد حاليًا مسار backend مستقل اسمه Managed Generation، ولا متغيرات إعداد مثل `MANAGED_OPENAI_API_KEY` أو `MANAGED_GEMINI_API_KEY` في `backend/app/config.py`.

## 3. النطاق المقترح للـ Sprint 4

### داخل النطاق

| المجال | المطلوب |
|---|---|
| Managed provider | اختيار مزوّد backend افتراضي وموديل صورة ونص، مع مفتاح server-side |
| إزالة BYOK من المنتج | حذف صفحة المفاتيح من التنقل، إزالة provider selector، إزالة رسائل “أضف مفتاحك” |
| توليد الصور | جعل الطلب يعتمد على إعداد backend لا على بيانات المستخدم |
| توليد الكابشنز | تشغيله بنفس managed provider، مع حفظ الناتج وإتاحة regenerate/edit/copy |
| الخطط | Free/Beta plan على الأقل، مع تعريف الرصيد وحدود الاستخدام |
| الرصيد | حجز رصيد قبل التوليد، خصم عند نجاح العملية، وإرجاعه عند الفشل القابل للإرجاع |
| سجل الاستهلاك | تسجيل المستخدم، العملية، المزوّد، الموديل، التكلفة التقديرية، والنتيجة |
| التخزين | حفظ الصور في Supabase Storage بمسارات مملوكة للمستخدم وروابط موقعة قصيرة العمر |
| التشغيل | health checks، timeouts، structured errors، logging آمن، ومراقبة فشل المزود |
| الدفع | عدم تحصيل أي مبلغ الآن، لكن تجهيز طبقة billing قابلة للتفعيل لاحقًا |

### خارج النطاق مؤقتًا

- ربط Stripe أو تحصيل أموال.
- شراء أرصدة.
- refunds أو invoices حقيقية.
- اختيار المستخدم لمزوّد مختلف.
- API keys من المستخدمين.
- auto-publishing إلى منصات التواصل.
- fallback تلقائي بين مزوّدين قبل وجود سياسة تكلفة واضحة.

## 4. تصميم Managed Generation

### إعدادات backend

ينبغي إضافة إعدادات سرية، مثل:

```env
MANAGED_IMAGE_PROVIDER=openai
MANAGED_IMAGE_MODEL=<approved-image-model>
MANAGED_TEXT_PROVIDER=openai
MANAGED_TEXT_MODEL=<approved-text-model>
MANAGED_OPENAI_API_KEY=<server-side-secret>
MANAGED_GEMINI_API_KEY=<server-side-secret-if-used>
GENERATION_BETA_MODE=true
DEFAULT_PLAN_CODE=beta
```

الأسماء النهائية قابلة للتعديل، لكن القاعدة غير قابلة للتفاوض: **لا يبدأ أي اسم لمفتاح سري بـ `NEXT_PUBLIC_`، ولا يُعاد إلى المتصفح، ولا يُحفظ في جدول عادي بصيغة نصية.**

يفضل استخدام Secret Manager الخاص بالاستضافة. إذا لم يكن متاحًا، يضاف المفتاح إلى متغيرات بيئة backend فقط. لا يفضل تخزين مفتاح TRENDY AI في `provider_keys` لأنه جدول مملوك للمستخدم منطقيًا ومصمم لـ BYOK.

### عقدة provider واحدة

إنشاء خدمة مثل `managed_provider.py` أو `provider_registry.py` تكون مسؤولة عن:

- قراءة provider/model من إعداد backend.
- الحصول على السر server-side.
- استدعاء image/text adapter الحالي.
- توحيد الأخطاء والـ request IDs.
- منع تمرير `api_key` من body أو query string.
- تسجيل metadata غير الحساسة فقط.

حقل `provider` في `generations` يبقى مفيدًا كسجل تاريخي، لكنه يصبح نتيجة backend لا اختيارًا من المستخدم. يجب ألا يكون body قادرًا على فرض `provider` أو `model`.

## 5. تغييرات الواجهة

### يجب إزالته

- رابط `/keys` من `app-sidebar.tsx`.
- صفحة `frontend/app/(dashboard)/[brandId]/keys/page.tsx` من المسار العام.
- `AddKeyModal`, `KeyCard`, `ProviderTabs`, `use-keys`, `use-active-keys` من مسار المنتج.
- `ProviderSelector` من `GeneratorForm`.
- شرط `hasActiveKey` الذي يعطل زر التوليد.
- روابط `review_your_keys` ورسائل `no_provider_key_yet`.
- فلاتر provider في history إذا لم تعد تعطي قيمة للمستخدم؛ أو إبقاؤها كفلتر تقني غير ظاهر فقط إن كان سجل المزوّد مفيدًا للإدارة.

### يجب أن يظهر بدلًا منه

- وصف واضح: “التوليد مُدار من TRENDY AI، ولا تحتاج لإضافة مفتاح.”
- رصيد المستخدم: `متبقي X من Y توليد`.
- حالة العملية: جاري التوليد، نجح، فشل، أو الرصيد غير كافٍ.
- رابط خطط/اشتراكات بسيط، مع عبارة واضحة أن الدفع غير متاح بعد في Beta.
- في مرحلة Beta، لا نعرض زر دفع وهمي؛ نعرض فقط الخطة الحالية وحدودها.

## 6. نموذج البيانات المقترح

### `plans`

| الحقل | الغرض |
|---|---|
| `code` | مثل `beta`, `starter`, `pro` |
| `name` | اسم العرض |
| `monthly_generation_credits` | الرصيد الشهري |
| `caption_credits_per_generation` | هل الكابشن داخل السعر أم له تكلفة منفصلة |
| `is_active` | تفعيل الخطة |
| `created_at`, `updated_at` | التتبع |

### `subscriptions`

حتى مع عدم وجود دفع، نحتاج سجلًا داخليًا واحدًا على الأقل لكل مستخدم:

- `user_id`
- `plan_code`
- `status`: `beta`, `active`, `past_due`, `canceled`
- `period_start`, `period_end`
- `provider_customer_id` و`provider_subscription_id` nullable للمستقبل
- timestamps

في Beta يمكن إنشاء subscription تلقائيًا عند إنشاء profile أو عند أول طلب.

### `credit_ledger`

لا تعتمدوا على رقم واحد يتم إنقاصه فقط؛ هذا يسبب مشاكل عند التزامن والتدقيق. الأفضل سجل حركة:

- `id`, `user_id`, `generation_id` nullable
- `operation_type`: `reserve`, `consume`, `release`, `adjustment`, `grant`
- `credits`
- `balance_after` أو snapshot متسق
- `idempotency_key`
- `reason`
- `created_at`

يمكن إضافة view أو helper لحساب الرصيد الحالي. إذا احتجنا أداء أعلى، نضيف `credit_balance` كـ cached balance، لكن يبقى ledger هو مصدر الحقيقة.

### `generation_usage`

سجل تكلفة منفصل عن سجل الصورة:

- `user_id`, `generation_id`
- `operation`: `image`, `caption`
- `provider`, `model`
- `status`: `reserved`, `succeeded`, `failed`, `released`
- `credits_charged`
- `estimated_provider_cost_usd` nullable
- `provider_request_id` nullable
- `input_metadata` آمن ومحدود، بلا prompt كامل إذا كان يحتوي بيانات حساسة
- `created_at`, `completed_at`

سبب فصل هذا الجدول: `generations` يصف المنتج الذي يراه المستخدم، بينما `generation_usage` يجيب عن سؤال الإدارة: كم كلفت العملية؟

### `generation_captions`

المشروع يملك contract للكابشن، لكن endpoint الحالي يعيد النتيجة ولا يحفظها. المطلوب حفظ:

- `generation_id`
- `language`, `platform`
- `caption`, `hook`, `hashtags`, `keywords`
- `model`, `prompt_version`
- `created_at`
- `is_current` أو ترتيب زمني واضح
- failure metadata إن لزم

## 7. سياسة الرصيد المؤقتة

اقتراح Beta قابل للتعديل:

- كل مستخدم جديد يأخذ رصيدًا مجانيًا ثابتًا مثل 10 image credits شهريًا.
- توليد الصورة يستهلك 1 credit في النسخة الأولى، بغض النظر عن المزوّد.
- أول caption على صورة ناجحة يكون ضمن generation نفسه أو يستهلك 0.25/0.5 credit حسب التكلفة الفعلية؛ القرار يجب تثبيته قبل UI.
- لا يتم خصم الرصيد عند فتح الصفحة أو فشل validation.
- يتم **حجز** الرصيد قبل طلب provider.
- عند النجاح يتحول الحجز إلى `consume`.
- عند timeout/network/provider failure يتم `release` مرة واحدة فقط.
- عند content-policy failure نحدد سياسة واضحة؛ المقترح في Beta هو release إذا لم يدفع المزود تكلفة فعلية أو تسجيلها كـ non-refundable إذا دفعناها.
- يجب منع طلبين متزامنين من استهلاك آخر credit نفسه.

الأفضل البدء بوحدة abstract اسمها `credit`, لا ربط الرصيد الآن بعدد صور ثابت داخل الواجهة؛ هذا يسهل إدخال أحجام وصيغ مختلفة لاحقًا.

## 8. التخزين

الصور لا ينبغي أن تبقى كرابط provider خارجي؛ الرابط قد ينتهي أو يتغير. المسار المقترح:

1. provider يعيد bytes.
2. backend يتحقق من MIME/type والحجم.
3. backend يطبق resize/watermark إن لزم.
4. يرفع الصورة إلى Storage داخل مسار مثل:

```text
users/{user_id}/brands/{brand_id}/generations/{generation_id}/image.webp
```

5. يحفظ `image_path` فقط في `generations`.
6. endpoint history/detail يولّد signed URL قصيرة العمر بدل public URL دائم.

يلزم أيضًا تحديد:

- maximum image size.
- retention policy للصور القديمة.
- ماذا يحدث عند حذف generation: حذف object أم soft delete؟
- هل المستخدم يستطيع تنزيل الصورة دون جلسة؟ المقترح: لا، استخدم signed URLs.
- هل التخزين المدفوع محسوب في التكلفة؟ يجب تسجيله لاحقًا إن أصبح مؤثرًا.

## 9. الأمان والاعتمادية التي لا يجوز تأجيلها

1. **Rate limiting:** حد لكل user وIP وbrand، وليس quota فقط. الرصيد يمنع التكلفة الطويلة لكنه لا يمنع الضغط على endpoint.
2. **Idempotency:** إعادة إرسال الطلب بسبب refresh أو double-click لا تنشئ صورتين ولا تخصم مرتين.
3. **Concurrency lock:** transaction أو RPC لحجز الرصيد ذريًا.
4. **Request timeout:** image provider قد يستغرق وقتًا طويلًا؛ يجب حفظ الحالة وعدم ترك generation في `processing` إلى الأبد.
5. **Recovery job:** مسار يعالج `pending/processing` القديمة ويضعها `failed` أو يعيد الرصيد حسب الحالة.
6. **Secrets hygiene:** لا تسجل headers أو مفاتيح أو prompts كاملة في logs.
7. **Prompt limits:** حدود طول للـ brief والحقول، وتنظيف المدخلات، وعدم السماح للمستخدم باختيار model أو endpoint.
8. **Provider errors:** فصل `invalid managed key`, `quota exhausted`, `rate limited`, `content policy`, `empty response`, و`storage failure` بدل رسالة عامة واحدة.
9. **Validation:** لا تسجل generation ناجحة قبل التأكد أن الصورة محفوظة فعليًا في Storage.
10. **Ownership/RLS:** كل query للصور والكابشنز والرصيد يجب أن يثبت ملكية المستخدم؛ service-role في backend لا يعني أن endpoint آمن تلقائيًا.
11. **Admin controls:** إيقاف التوليد globally، تغيير الخطة/الرصيد، رؤية الفشل والتكلفة، وتغيير provider/model بدون deploy إن أمكن.
12. **Data privacy:** brand kit والـ prompts قد تحتوي معلومات تجارية؛ نحدد retention وحق الحذف قبل الإطلاق العام.

## 10. سبب محتمل آخر لمشكلة “المفتاح موجود لكن لا توجد صورة”

حتى بعد إضافة managed key، يجب اختبار هذه النقاط تحديدًا:

- هل `SUPABASE_URL` و`SUPABASE_SECRET_KEY` وVault RPC migrations مطبقة على نفس مشروع Supabase؟
- هل الموديل المطلوب يدعم image generation على endpoint الحالي؟
- هل الحساب لديه billing/credits عند مزود الصور؟ وجود API key صالح لا يعني وجود رصيد.
- هل response يرجع `b64_json` فعلًا؟ بعض النماذج أو endpoints ترجع URL أو schema مختلفًا.
- هل الصورة تحفظ في Storage بعد استلامها؟ قد يكون فشل التخزين بعد نجاح provider.
- هل رابط الصورة الناتج public أو signed وصالح؟ `history` حاليًا يبني public URL من `image_path`.
- هل الـ backend runtime يقرأ `.env` من مجلد العمل الصحيح؟
- هل Docker/Render يمرر الأسرار إلى backend process وليس frontend build؟
- هل `tiktok_video` موجود ضمن image presets رغم أن endpoint الحالي صورة؟ هذا تناقض منتجي يجب منعه أو تغييره.
- هل الفشل الظاهر في الواجهة مجرد رسالة عامة تخفي `request_id`؟ يجب حفظ request ID للإدارة دون عرضه كسر.

## 11. خطة التنفيذ المرحلية

### S4.1 — تشغيل provider مُدار

- إضافة managed provider configuration.
- إضافة resolver واحد للصورة والكابشن.
- تعديل generation endpoint ليمنع `provider` و`model` من request body.
- اختبار mocked provider ثم اختبار تكاملي يدوي بمفتاح backend.
- إضافة health check آمن لا يكشف المفتاح.

**خروج المرحلة:** المستخدم يستطيع التوليد بدون صفحة Keys وبدون إرسال أي credential من المتصفح.

### S4.2 — إزالة BYOK من UX

- إزالة navigation والصفحات والhooks والرسائل المرتبطة بالمفاتيح.
- إزالة provider selector وactive-key gating.
- تحديث النصوص العربية والإنجليزية.
- الإبقاء مؤقتًا على legacy endpoints خلف admin-only أو إرجاع `410 BYOK_DISABLED`، وعدم حذفها فجأة قبل التأكد من عدم وجود clients قديمة.

**خروج المرحلة:** لا يوجد في المسار العادي أي اختيار بين BYOK وManaged.

### S4.3 — quota وusage

- migrations للخطط والاشتراكات وledger وusage.
- إنشاء Beta subscription تلقائيًا.
- reserve/consume/release ذري.
- idempotency وrate limit.
- endpoint يعيد plan + remaining credits.

**خروج المرحلة:** كل عملية لها تكلفة داخلية وسجل قابل للتدقيق، حتى بدون دفع.

### S4.4 — captions والتخزين

- حفظ caption history.
- signed URLs للصور.
- اختبار فشل caption دون إفساد الصورة.
- اختبار حذف generation وتنظيف storage.

**خروج المرحلة:** الصورة والكابشن قابلان للاسترجاع من history، ولا يعتمد النظام على روابط provider مؤقتة.

### S4.5 — التشغيل والتحقق

- Docker/Render environment variables.
- smoke test: signup → brand → brief → image → caption → history → download.
- failure matrix للمفتاح، provider quota، timeout، policy، storage، insufficient credits.
- dashboard إداري للتكلفة والنجاح والفشل والاستهلاك.

## 12. Acceptance criteria

- المستخدم لا يستطيع إدخال API key ولا اختيار BYOK.
- لا يوجد API key في network requests من browser.
- توليد الصورة يعمل بمفتاح backend فقط.
- توليد الكابشن يعمل بمفتاح backend فقط.
- provider/model يحدده backend ويظهر فقط كـ metadata داخلي.
- لا يمكن تجاوز quota بتغيير `brand_id` أو إعادة إرسال الطلب.
- كل generation لها usage record وidempotency key.
- الفشل يرجع الرصيد وفق سياسة محددة، ولا يترك reservations معلقة.
- الصور محفوظة في Storage المملوك للمشروع مع signed URLs.
- الكابشنات محفوظة وقابلة لإعادة التوليد دون إعادة توليد الصورة.
- خطة Beta واضحة للمستخدم، ولا توجد شاشة دفع أو مطالبة مالية قبل تفعيل billing.
- اختبارات backend وfrontend تمر، مع smoke test حقيقي في بيئة staging.

## 13. قرار مقترح قبل بدء البرمجة

أوصي بالبدء بـ **OpenAI كـ managed image/text provider واحد** في Beta، لا OpenAI وGemini معًا. السبب ليس تقنيًا فقط؛ تشغيل مزودين يضاعف اختلافات الموديلات، response schemas، التسعير، والفشل. بعد نجاح المسار الأساسي نضيف provider adapter ثانيًا خلف backend feature flag، من غير أن يظهر الاختيار للمستخدم.

كما أوصي بعدم تسمية الخطط “اشتراكات مدفوعة” في الواجهة قبل الدفع. استخدموا `Beta plan` و`free credits` الآن، مع نفس نموذج البيانات الذي سيستقبل Stripe لاحقًا.
