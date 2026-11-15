"""Bilingual deterministic result templates; no provider calls."""

def render_assessment(assessment, language):
    ar = getattr(language, 'value', language) == 'ar'
    facts = assessment.facts
    sections = []
    def add(code, en_title, ar_title, en, arabic):
        sections.append((assessment.variable_id+'_'+code, ar_title if ar else en_title, arabic if ar else en))
    add('judgment', 'What can we conclude?', 'ما الذي نستنتجه؟', assessment.headline, assessment.headline)
    if assessment.judgment:
        add('inference_judgment', 'Statistical judgment', 'حكم الاستدلال الإحصائي',
            assessment.judgment['message'], assessment.judgment['message'])
    if facts.slope_per_year is not None:
        number = f'{facts.slope_per_year:.8g}'
        quantity_ar = '\u2066'+f'{number} {facts.slope_unit}'+'\u2069'
        number_ar = '\u2066'+number+'\u2069'
        if assessment.descriptive_status == 'available':
            add('annual', 'Meaning of the estimate', 'معنى التقدير',
                f'Annual descriptive Theil–Sen slope: {number} {facts.slope_unit}, from {facts.complete_years} complete annual observations. It describes the selected period; it is not a forecast or evidence of cause.',
                f'ميل Theil–Sen السنوي الوصفي: {quantity_ar}، من {facts.complete_years} قيم سنوية مكتملة. يصف الفترة المختارة، ولا يمثل توقعًا للمستقبل أو دليلًا على السبب.')
            if assessment.variable_id == 'air_temperature' and facts.monthly_unit == 'K':
                add('temperature_units', 'Temperature-change units', 'وحدة تغيّر الحرارة',
                    f'A temperature change of 1 K equals a change of 1 °C. This slope is also {number} °C/year.',
                    f'التغيّر بمقدار 1 كلفن يساوي تغيّرًا بمقدار درجة مئوية واحدة؛ لذلك الميل يساوي أيضًا {number_ar} درجة مئوية سنويًا.')
        else:
            add('annual', 'Stored estimate needs review', 'التقدير المحفوظ يحتاج مراجعة',
                f'Stored slope: {number} {facts.slope_unit}. Do not interpret its direction until the evidence checks pass.',
                f'الميل المحفوظ: {quantity_ar}. لا تفسّر اتجاهه قبل اجتياز فحوص تطابق الأدلة.')
    if facts.mean_monthly_value is not None:
        conversion = f' (approximately {facts.mean_celsius:.2f} °C)' if facts.mean_celsius is not None else ''
        conversion_ar = f' (حوالي {facts.mean_celsius:.2f} درجة مئوية)' if facts.mean_celsius is not None else ''
        add('monthly', 'Monthly values', 'القيم الشهرية',
            f'The arithmetic mean of {facts.valid_months} valid displayed monthly values is {facts.mean_monthly_value:.6g} {facts.monthly_unit}{conversion}. Monthly completeness and spatial coverage describe different things.',
            f'المتوسط الحسابي لـ{facts.valid_months} قيمة شهرية صالحة معروضة هو {facts.mean_monthly_value:.6g} {facts.monthly_unit}{conversion_ar}. اكتمال الشهور والتغطية المكانية مقياسان مختلفان.')
    if facts.retained_cells is not None:
        add('support', 'Which area does this describe?', 'النتيجة تمثل أي مساحة؟',
            f'QA retained {facts.retained_cells} of {facts.selected_cells} selected cells, representing {facts.retained_area_fraction*100:.1f}% of selected native-cell area. Cell-slope signs do not identify statistically significant cells.',
            f'احتفظ فحص الجودة بـ{facts.retained_cells} من {facts.selected_cells} خلية مختارة، تمثل {facts.retained_area_fraction*100:.1f}% من مساحة الخلايا المختارة. إشارة ميل الخلية لا تحدد دلالتها الإحصائية.')
    if facts.leave_one_year_out_windows is not None:
        lower_ar = '\u2066'+f'{facts.leave_one_year_out_min_slope:.8g}'+'\u2069'
        upper_ar = '\u2066'+f'{facts.leave_one_year_out_max_slope:.8g}'+'\u2069'
        add('sensitivity', 'Sensitivity to individual years', 'الحساسية للسنوات المنفردة',
            f'Leave-one-year-out slopes range from {facts.leave_one_year_out_min_slope:.8g} to {facts.leave_one_year_out_max_slope:.8g} {facts.slope_unit}. The sign agrees in {facts.leave_one_year_out_same_sign_count}/{facts.leave_one_year_out_windows} checks. This is not a confidence interval or a probability that the trend is real.',
            f'عند حذف سنة واحدة في كل تجربة، تراوح الميل من {lower_ar} إلى {upper_ar} {facts.slope_unit}. وافقت الإشارة النتيجة الأصلية في {facts.leave_one_year_out_same_sign_count}/{facts.leave_one_year_out_windows} تجربة. هذا ليس فترة ثقة أو احتمالًا لصحة الاتجاه.')
    for reason in assessment.reasons:
        add(reason.code, 'Interpretation limit' if reason.severity=='blocking' else 'Review note',
            'حدود الاستنتاج' if reason.severity=='blocking' else 'ملاحظة للمراجعة', reason.message, reason.message)
    return sections
