"""One question -> scope/intent -> cited retrieval -> executable descriptive proposal."""
import re
from packages.rag.arabic import normalize_query
from packages.rag.intent import classify_query


def plan_question(query, data, catalog, region_id=None, start_month=None, end_month=None, language='en'):
    normalized = normalize_query(query).lower()
    intent = classify_query(query)
    regions = data.list_regions()
    matches = []
    for region in regions:
        aliases = [region.region_id, *region.aliases]
        if any(re.search(r'(?<!\w)'+re.escape(normalize_query(a).lower())+r'(?!\w)', normalized) for a in aliases):
            matches.append(region.region_id)
    state = 'ready'
    reason = None
    if len(matches) > 1:
        state, reason = 'clarification_required', 'multiple_regions'
    elif matches:
        region_id = matches[0]
    location = re.search(r'(?:\bin\b|(?<!\w)في)\s+(.+)', normalized)
    if location and not matches and not re.match(r'(?:\d|kelvin|celsius|nasa|the data|soil|كلفن|البيانات|التربة|الماضي|السنين)', location[1]):
        state, reason = 'clarification_required', 'unresolved_named_area'
    if any(re.search(r'(?<!\w)'+re.escape(normalize_query(a).lower())+r'(?!\w)', normalized)
           for a in ['sinai', 'سيناء', 'سينا', 'new york', 'paris', 'القاهرة', 'cairo']):
        state, reason = 'unsupported', 'region_not_registered'
    ids = intent.get('variable_ids', [])
    if intent['status'] in ('unsupported', 'unavailable', 'ambiguous'):
        state = 'clarification_required' if intent['status']=='ambiguous' else intent['status']
        reason = intent.get('reason_code')
    elif len(ids) != 1:
        state, reason = 'clarification_required', 'choose_one_variable'
    elif not region_id and state == 'ready':
        state, reason = 'clarification_required', 'choose_region'
    region = data.get_region(region_id) if region_id else None
    years = re.findall(r'\b(?:19\d{2}|20\d{2})\b', query)
    if years:
        start_month, end_month = years[0]+'-01', years[-1]+'-12'
    start_month = start_month or (region.period_start if region else '2001-01')
    end_month = end_month or (region.period_end if region else '2024-12')
    availability = None
    if state == 'ready':
        if start_month > end_month:
            state, reason = 'unavailable', 'invalid_period_order'
        else:
            availability = catalog.check_availability(variable_id=ids[0], region_id=region_id,
                start_month=start_month, end_month=end_month)
            if not availability.usable:
                state, reason = 'unavailable', str(getattr(availability.reason_code, 'value', availability.reason_code))
    messages = {
        'ready': ('A descriptive analysis of the registered study rectangle is available. It is not an exact administrative boundary; review the map and period before starting.', 'يوجد تحليل وصفي لمستطيل الدراسة المسجل، وليس حدودًا إدارية دقيقة. راجع الخريطة والفترة قبل تشغيله.'),
        'clarification_required': ('Choose one supported variable and one registered region; drought alone does not identify a unique variable.', 'حدد متغيرًا واحدًا ومنطقة متاحة؛ الجفاف وحده لا يحدد متغيرًا واحدًا.'),
        'unsupported': ('The requested topic or named area is outside supported scope.', 'الموضوع أو المنطقة المذكورة خارج النطاق المدعوم.'),
        'unavailable': ('The requested analysis is not available for this period or coverage.', 'التحليل المطلوب غير متاح لهذه الفترة أو التغطية.')}
    proposal = {'region_id': region_id, 'variable_ids': ids, 'start_month': start_month,
                'end_month': end_month, 'aggregation_policy': 'area_weighted'} if state=='ready' else None
    return {'state': state, 'reason_code': reason, 'region_id': region_id, 'variable_ids': ids,
            'analysis_request': proposal, 'message': messages[state][language=='ar'],
            'availability': availability.model_dump(mode='json') if availability else None}
