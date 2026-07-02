"""Translations and localization helpers for the Forex Bias Dashboard."""

from typing import Dict, Any, Optional

TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    "en": {
        "title": "Forex Bias Dashboard",
        "lang_label": "Language / Язык",
        "view_dashboard": "Dashboard",
        "view_learn": "Education & Help",
        "learn_btn_label": "Go to Education / Help Page 📖",
        "back_btn_label": "⬅ Back to Dashboard",
        # Page contents
        "verdict_lbl": "Verdict",
        "normalized_score_lbl": "Normalized score",
        "data_coverage_lbl": "Data coverage",
        "weight_lbl": "weight",
        "partial_data_warn": "⚠️ Verdict is based on partial data. Missing categories are excluded from the normalized score.",
        "unavailable_categories": "Unavailable",
        "partial_categories": "Partial data",
        "daily_close_title": "EUR/USD Daily Close",
        "chart_levels": "Chart Levels",
        "override_caption": "Override current EUR/USD when your broker feed is more accurate.",
        "override_checkbox": "Override current EUR/USD",
        "current_eurusd": "Current EUR/USD",
        "monthly_structure": "Monthly Structure",
        "weekly_structure": "Weekly Structure",
        "monthly_open": "Monthly Open",
        "weekly_open": "Weekly Open",
        "cot_net": "COT EUR net position",
        "cot_change": "COT weekly change",
        "cot_unavailable": "COT data unavailable",
        "prev_week_high_low": "Previous week high / low",
        "dxy_direction": "DXY direction",
        "dxy_unavailable": "DXY data unavailable",
        "macro_regime": "Macro Regime",
        "regime_lbl": "Regime",
        "rates_yield": "Rates & Yield Curve",
        "inflation": "Inflation",
        "labor_market": "Labor Market",
        "liquidity": "Liquidity",
        "growth": "Growth",
        "yield_spread": "Yield Spread (10Y−2Y)",
        "net_liquidity": "Net Liquidity (WALCL−TGA−RRP)",
        "yield_spread_unavail": "Yield spread unavailable",
        "net_liquidity_unavail": "Net liquidity unavailable",
        "category_score_summary": "Category Score Summary",
        "all_fred_series": "All FRED macro series",
        "economic_calendar": "Economic Calendar",
        "economic_calendar_source": "Source: {source} — informational only, not used in scoring.",
        "news_warning": "⚠️ High impact EUR/USD news is within the next 60 minutes.",
        "other_events_today": "Other high-impact events today",
        "data_status": "Data Status",
        "dataset": "Dataset",
        "source": "Source",
        "calendar_info_caption": "Calendar events are informational only and do not contribute to the bias score.",
        "diagnostics_title": "Diagnostics & Data Freshness",
        "diagnostics_caption": "Detailed view of mathematical weight renormalization and underlying data points.",
        "renormalization_title": "Category Contributions & Renormalization",
        "factor_details_title": "Underlying Factor Details",
        # Diagnostics columns
        "col_category": "Category",
        "col_weight": "Weight",
        "col_score": "Score",
        "col_avail": "Avail",
        "col_status": "Status",
        "col_base_weight": "Base Weight",
        "col_renorm_weight": "Renormalized Weight",
        "col_cat_score": "Category Score",
        "col_norm_contrib": "Normalized Contribution",
        "col_factor": "Factor",
        "col_signal": "Signal",
        "col_timestamp": "Timestamp",
        "col_freshness": "Freshness",
        "fresh_val": "🟢 Fresh",
        "stale_val": "🔴 Stale",
        "unknown_val": "⚪ Unknown",
        "no_factors": "No factors.",
        "flat_val": "Flat",
        "rising_val": "Rising",
        "falling_val": "Falling",
        
        # Learn Page specific
        "learn_title": "Education & Dashboard Mechanics",
        "learn_intro": "This page explains how the Forex Bias Dashboard works, the underlying macro data, and the scoring logic.",
        
        "section_what_dashboard": "1. What is the Forex Bias Dashboard?",
        "what_dashboard_text": (
            "This dashboard aggregates structural price action and macroeconomic indicators "
            "to assess the medium-term fundamental bias for the EUR/USD currency pair.\n\n"
            "By looking at monthly and weekly market structures combined with key macroeconomic data "
            "(interest rates, inflation, labor market, liquidity, and growth), the dashboard calculates "
            "a single normalized score between -1.0 (strong USD bias / bearish EUR/USD) and +1.0 (strong EUR bias / bullish EUR/USD)."
        ),
        
        "section_what_cot": "2. What is COT (Commitment of Traders)?",
        "what_cot_text": (
            "The **Commitment of Traders (COT)** report is published weekly by the CFTC. It shows the holdings of participants in the US futures markets.\n\n"
            "This dashboard monitors **Euro FX futures non-commercial net positions** (large speculators, e.g., hedge funds).\n"
            "- **Net Position**: Speculative long minus short contracts. A positive net position (+1.0 signal) suggests institutional support for EUR, while negative net position (-1.0 signal) suggests institutional preference for USD.\n"
            "- **Weekly Change**: Indicates whether speculators are increasing (+1.0 signal) or decreasing (-1.0 signal) their net exposure week-over-week."
        ),
        
        "section_what_fed": "3. What is the FED and Macro Data?",
        "what_fed_text": (
            "The **Federal Reserve (Fed)** controls US monetary policy, which is the primary driver of global FX markets. The dashboard monitors these FRED data feeds:\n\n"
            "- **Rates & Yield Curve**: Federal Funds Rate and treasury yields. Higher or rising US yields attract capital to USD, creating a bearish signal for EUR/USD.\n"
            "- **Yield Spread (10Y-2Y)**: An inverting yield curve (10Y yield minus 2Y yield going below 0) indicates late-cycle economic slowdowns and can lead to risk-off flows into USD.\n"
            "- **Inflation**: CPI, PCE, and Sticky CPI. Rising inflation forces the Fed to raise interest rates, strengthening the USD (bearish EUR/USD).\n"
            "- **Labor Market**: Payrolls, Unemployment, and Jobless Claims. A robust labor market gives the Fed room to stay hawkish (bearish EUR/USD).\n"
            "- **Growth**: GDP, Retail Sales, and Industrial Production. Stronger US economic growth generally strengthens the greenback."
        ),
        
        "section_what_liquidity": "4. What is Net Liquidity?",
        "what_liquidity_text": (
            "**Net Liquidity** measures the active supply of dollars in the financial system. It is calculated as:\n\n"
            "$$\\text{Net Liquidity} = \\text{Fed Balance Sheet (WALCL)} - \\text{Treasury General Account (TGA)} - \\text{Reverse Repo (RRP)}$$\n\n"
            "- When Net Liquidity rises, risk assets and currency pairs like EUR/USD tend to rise (+1.0 signal).\n"
            "- When Net Liquidity falls, dollar liquidity tightens, supporting the USD (-1.0 signal)."
        ),
        
        "section_how_counted": "5. How is it counted (Scoring Mechanics)?",
        "how_counted_text": (
            "**Step 1: Factor Signaling**\n"
            "Each individual factor is mapped to a signal in the range `[-1.0, +1.0]`:\n"
            "- `+1.0`: Bullish EUR/USD (supports EUR, weakens USD)\n"
            "- `0.0`: Neutral / flat\n"
            "- `-1.0`: Bearish EUR/USD (weakens EUR, strengthens USD)\n"
            "- `None`: If a factor is unavailable, it is excluded completely (no fallback/mock data).\n\n"
            "**Step 2: Category Scoring**\n"
            "Factors are grouped into 7 categories. The category score is the average of all available signals in that category:\n"
            "$$\\text{Category Score} = \\frac{\\sum \\text{Available signals}}{\\text{Count of available factors}}$$\n\n"
            "**Step 3: Weight Renormalization & Final Score**\n"
            "Each category has a base weight. If some categories are completely unavailable, the weights of the remaining categories are renormalized to sum to 100%:\n"
            "$$\\text{Renormalized Weight}_i = \\frac{\\text{Base Weight}_i}{\\sum_{j \\in \\text{Available}} \\text{Base Weight}_j}$$\n"
            "$$\\text{Final Score} = \\sum_{i \\in \\text{Available}} (\\text{Category Score}_i \\times \\text{Renormalized Weight}_i)$$\n\n"
            "**Step 4: Classification**\n"
            "The final score determines the bias verdict:\n"
            "- `[0.70, 1.00]`: **Strong Bullish EUR/USD**\n"
            "- `[0.50, 0.69]`: **Bullish EUR/USD**\n"
            "- `[-0.49, 0.49]`: **Neutral / Mixed**\n"
            "- `[-0.69, -0.50]`: **Bearish EUR/USD**\n"
            "- `[-1.00, -0.70]`: **Strong Bearish EUR/USD**"
        ),
    },
    "ru": {
        "title": "Панель Макросмещения EUR/USD",
        "lang_label": "Язык / Language",
        "view_dashboard": "Панель инструментов",
        "view_learn": "Обучение и справка",
        "learn_btn_label": "Перейти к обучению / справке 📖",
        "back_btn_label": "⬅ Назад к панели инструментов",
        # Page contents
        "verdict_lbl": "Вердикт",
        "normalized_score_lbl": "Нормализованный балл",
        "data_coverage_lbl": "Покрытие данных",
        "weight_lbl": "вес",
        "partial_data_warn": "⚠️ Вердикт основан на частичных данных. Отсутствующие категории исключены из расчета нормализованного балла.",
        "unavailable_categories": "Недоступно",
        "partial_categories": "Частичные данные",
        "daily_close_title": "Дневное закрытие EUR/USD",
        "chart_levels": "Уровни графика",
        "override_caption": "Переопределите текущую цену EUR/USD, если данные вашего брокера точнее.",
        "override_checkbox": "Переопределить EUR/USD",
        "current_eurusd": "Текущий EUR/USD",
        "monthly_structure": "Месячная структура",
        "weekly_structure": "Недельная структура",
        "monthly_open": "Открытие месяца",
        "weekly_open": "Открытие недели",
        "cot_net": "Чистая позиция COT EUR",
        "cot_change": "Изменение COT за неделю",
        "cot_unavailable": "Данные COT недоступны",
        "prev_week_high_low": "Максимум / минимум прошлой недели",
        "dxy_direction": "Направление DXY",
        "dxy_unavailable": "Данные DXY недоступны",
        "macro_regime": "Макроэкономический режим",
        "regime_lbl": "Режим",
        "rates_yield": "Ставки и кривая доходности",
        "inflation": "Инфляция",
        "labor_market": "Рынок труда",
        "liquidity": "Ликвидность",
        "growth": "Экономический рост",
        "yield_spread": "Спред доходности (10Y−2Y)",
        "net_liquidity": "Чистая ликвидность (WALCL−TGA−RRP)",
        "yield_spread_unavail": "Спред доходности недоступен",
        "net_liquidity_unavail": "Чистая ликвидность недоступна",
        "category_score_summary": "Сводка баллов по категориям",
        "all_fred_series": "Все макроэкономические ряды FRED",
        "economic_calendar": "Экономический календарь",
        "economic_calendar_source": "Источник: {source} — только для информации, не используется при подсчете баллов.",
        "news_warning": "⚠️ Важные новости по EUR/USD ожидаются в течение следующих 60 минут.",
        "other_events_today": "Другие важные события на сегодня",
        "data_status": "Статус данных",
        "dataset": "Набор данных",
        "source": "Источник",
        "calendar_info_caption": "События календаря носят исключительно информационный характер и не влияют на балл смещения.",
        "diagnostics_title": "Диагностика и свежесть данных",
        "diagnostics_caption": "Подробный вид математической ренормализации весов и базовых показателей.",
        "renormalization_title": "Вклад категорий и ренормализация",
        "factor_details_title": "Подробности по отдельным факторам",
        # Diagnostics columns
        "col_category": "Категория",
        "col_weight": "Вес",
        "col_score": "Балл",
        "col_avail": "Доступно",
        "col_status": "Статус",
        "col_base_weight": "Базовый вес",
        "col_renorm_weight": "Ренормализованный вес",
        "col_cat_score": "Балл категории",
        "col_norm_contrib": "Нормализованный вклад",
        "col_factor": "Фактор",
        "col_signal": "Сигнал",
        "col_timestamp": "Время",
        "col_freshness": "Свежесть",
        "fresh_val": "🟢 Свежие",
        "stale_val": "🔴 Устаревшие",
        "unknown_val": "⚪ Неизвестно",
        "no_factors": "Нет факторов.",
        "flat_val": "Флэт",
        "rising_val": "Растет",
        "falling_val": "Падает",
        
        # Learn Page specific
        "learn_title": "Обучение и устройство панели",
        "learn_intro": "На этой странице объясняется, как работает панель макросмещения Forex, какие макроданные лежат в её основе и как устроен расчет баллов.",
        
        "section_what_dashboard": "1. Что такое панель макросмещения Forex?",
        "what_dashboard_text": (
            "Эта панель объединяет ценовую структуру рынка и макроэкономические показатели "
            "для оценки среднесрочного фундаментального смещения валютной пары EUR/USD.\n\n"
            "Анализируя месячную и недельную структуру цены в сочетании с ключевыми макроэкономическими показателями "
            "(процентные ставки, инфляция, рынок труда, ликвидность и экономический рост), панель рассчитывает "
            "единый нормализованный балл в диапазоне от -1.0 (сильное смещение в пользу USD / падение EUR/USD) до +1.0 (сильное смещение в пользу EUR / рост EUR/USD)."
        ),
        
        "section_what_cot": "2. Что такое COT (Commitment of Traders)?",
        "what_cot_text": (
            "Отчет **Commitment of Traders (COT)** еженедельно публикуется Комиссией по торговле товарными фьючерсами США (CFTC). Он показывает позиции участников на рынке фьючерсов.\n\n"
            "Наша панель отслеживает **чистые позиции некоммерческих трейдеров по фьючерсам на Euro FX** (крупные спекулянты, такие как хедж-фонды).\n"
            "- **Чистая позиция (Net Position)**: Разница между длинными (long) и короткими (short) спекулятивными контрактами. Положительное значение (+1.0 к сигналу) указывает на институциональную поддержку евро, тогда как отрицательное (-1.0 к сигналу) — на предпочтение доллара.\n"
            "- **Недельное изменение (Weekly Change)**: Показывает, наращивают спекулянты чистую позицию по евро (+1.0) или сокращают (-1.0) по сравнению с прошлой неделей."
        ),
        
        "section_what_fed": "3. Что такое ФРС и макроданные?",
        "what_fed_text": (
            "**Федеральная резервная система (ФРС / Fed)** определяет монетарную политику США, которая является главным драйвером глобального валютного рынка. Панель отслеживает следующие данные FRED:\n\n"
            "- **Ставки и кривая доходности (Rates & Yield Curve)**: Ставка по федеральным фондам и доходность казначейских облигаций США. Рост доходностей в США привлекает капитал в доллар, давая медвежий сигнал для EUR/USD.\n"
            "- **Спред доходности (Yield Spread 10Y-2Y)**: Инверсия кривой доходности (когда спред между 10-летними и 2-летними облигациями уходит ниже нуля) указывает на замедление экономики в конце цикла и может приводить к бегству в доллар как защитный актив.\n"
            "- **Инфляция (Inflation)**: Индексы CPI, PCE и Sticky CPI. Рост инфляции вынуждает ФРС повышать ставки, укрепляя доллар США (медвежий сигнал для EUR/USD).\n"
            "- **Рынок труда (Labor Market)**: Число рабочих мест (Payrolls), уровень безработицы (Unemployment) и заявки на пособия по безработице (Claims). Крепкий рынок труда развязывает руки ФРС для жесткой политики (медвежий сигнал для EUR/USD).\n"
            "- **Экономический рост (Growth)**: ВВП (GDP), розничные продажи (Retail Sales) и промышленное производство (Industrial Production). Более сильный рост экономики США укрепляет доллар."
        ),
        
        "section_what_liquidity": "4. Что такое чистая ликвидность (Net Liquidity)?",
        "what_liquidity_text": (
            "**Чистая ликвидность** измеряет активное предложение долларов в финансовой системе. Она рассчитывается по формуле:\n\n"
            "$$\\text{Чистая ликвидность} = \\text{Баланс ФРС (WALCL)} - \\text{Единый казначейский счет (TGA)} - \\text{Обратное репо (RRP)}$$\n\n"
            "- Когда чистая ликвидность растет, рисковые активы и курс EUR/USD обычно растут (+1.0 к сигналу).\n"
            "- Когда чистая ликвидность падает, долларовая ликвидность сжимается, поддерживая доллар (-1.0 к сигналу)."
        ),
        
        "section_how_counted": "5. Как рассчитываются баллы (Механика скоринга)?",
        "how_counted_text": (
            "**Шаг 1: Сигналы отдельных факторов**\n"
            "Каждый фактор преобразуется в сигнал в диапазоне `[-1.0, +1.0]`:\n"
            "- `+1.0`: Бычий сигнал для EUR/USD (поддержка EUR, ослабление USD)\n"
            "- `0.0`: Нейтрально / без изменений\n"
            "- `-1.0`: Медвежий сигнал для EUR/USD (ослабление EUR, поддержка USD)\n"
            "- `None`: Если фактор недоступен, он полностью исключается из расчетов (без фиктивных данных).\n\n"
            "**Шаг 2: Средний балл категории**\n"
            "Факторы сгруппированы в 7 категорий. Балл категории — это среднее арифметическое доступных сигналов этой категории:\n"
            "$$\\text{Балл категории} = \\frac{\\sum \\text{Доступные сигналы}}{\\text{Количество доступных факторов}}$$\n\n"
            "**Шаг 3: Ренормализация весов и итоговый балл**\n"
            "Каждая категория имеет базовый вес. Если какие-то категории полностью отсутствуют, веса оставшихся динамически пересчитываются так, чтобы в сумме давать 100%:\n"
            "$$\\text{Ренормализованный вес}_i = \\frac{\\text{Базовый вес}_i}{\\sum_{j \\in \\text{Доступные}} \\text{Базовый вес}_j}$$\n"
            "$$\\text{Итоговый балл} = \\sum_{i \\in \\text{Доступные}} (\\text{Балл категории}_i \\times \\text{Ренормализованный вес}_i)$$\n\n"
            "**Шаг 4: Классификация**\n"
            "Итоговый балл определяет итоговое смещение (вердикт):\n"
            "- `[0.70, 1.00]`: **Сильное бычье смещение EUR/USD (Strong Bullish)**\n"
            "- `[0.50, 0.69]`: **Бычье смещение EUR/USD (Bullish)**\n"
            "- `[-0.49, 0.49]`: **Нейтральное / Смешанное (Neutral / Mixed)**\n"
            "- `[-0.69, -0.50]`: **Медвежье смещение EUR/USD (Bearish)**\n"
            "- `[-1.00, -0.70]`: **Сильное медвежье смещение EUR/USD (Strong Bearish)**"
        ),
    }
}

# Lookup dictionaries for items that are generated dynamically by the engines
STRING_MAP: Dict[str, Dict[str, str]] = {
    "ru": {
        "Monthly Structure": "Месячная структура",
        "Weekly Structure": "Недельная структура",
        "Rates & Yield Curve": "Ставки и кривая доходности",
        "Inflation": "Инфляция",
        "Labor": "Рынок труда",
        "Liquidity": "Ликвидность",
        "Growth": "Экономический рост",
        
        "Monthly Opening Range": "Месячный диапазон открытия",
        "COT Net Position": "Чистая позиция COT",
        "COT Weekly Change": "Недельное изменение COT",
        "Weekly Opening Range": "Недельный диапазон открытия",
        "DXY Direction": "Направление DXY",
        "Fed Policy": "Политика ФРС",
        "Yield Curve Direction": "Направление кривой доходности",
        "Yield Spread Direction": "Направление спреда доходности",
        "CPI Direction": "Направление CPI",
        "PCE Direction": "Направление PCE",
        "Sticky CPI Direction": "Направление Sticky CPI",
        "Payrolls Direction": "Направление Payrolls",
        "Unemployment Direction": "Направление безработицы",
        "Initial Claims Direction": "Направление первичных заявок",
        "Net Liquidity Direction": "Направление чистой ликвидности",
        "SOFR Direction": "Направление SOFR",
        "GDP Direction": "Направление ВВП",
        "Retail Sales Direction": "Направление розничных продаж",
        "Industrial Production Direction": "Направление промпроизводства",

        # COT reasons
        "EUR net position is positive": "Чистая позиция по EUR положительная",
        "EUR net position is negative": "Чистая позиция по EUR отрицательная",
        "EUR net position is flat": "Чистая позиция по EUR нейтральная",
        "EUR net position increased week over week": "Чистая позиция по EUR увеличилась за неделю",
        "EUR net position decreased week over week": "Чистая позиция по EUR уменьшилась за неделю",
        "EUR net position unchanged week over week": "Чистая позиция по EUR не изменилась за неделю",

        # DXY & FED reasons
        "DXY is falling": "DXY снижается",
        "DXY is rising": "DXY растет",
        "Fed Funds rate is falling": "Ставка по федеральным фондам снижается",
        "Fed Funds rate is rising": "Ставка по федеральным фондам растет",
        "Yield spread is steepening (10Y−2Y widening)": "Спред доходности крутеет (10Y−2Y расширяется)",
        "Yield spread is flattening (10Y−2Y narrowing)": "Спред доходности сглаживается (10Y−2Y сужается)",
        "No yield data": "Нет данных по доходностям",

        # Opening ranges reasons & states
        "Monthly range unavailable": "Месячный диапазон недоступен",
        "Monthly open range unavailable": "Диапазон открытия месяца недоступен",
        "Weekly range unavailable": "Недельный диапазон недоступен",
        "Weekly open range unavailable": "Диапазон открытия недели недоступен",
        "Range data missing": "Данные диапазона отсутствуют",
        "No range context available": "Контекст диапазона недоступен",
        "No monthly context": "Месячный контекст отсутствует",
        "Inside range": "Внутри диапазона",
        "Above range": "Выше диапазона",
        "Below range": "Ниже диапазона",
        "raid high": "рейд сверху",
        "raid low": "рейд снизу",
        "no raid yet": "рейдов нет",

        # Dynamic range details
        "Monthly Open (D)": "Открытие месяца (D)",
        "Monthly Open (W)": "Открытие месяца (W)",
        "Weekly Open (4H)": "Открытие недели (4H)",
        "Weekly Open (D)": "Открытие недели (D)",
        "Weekly Open (Sunday)": "Открытие недели (Sunday)",
        
        "Price is inside the active Monthly Open D range": "Цена внутри активного диапазона открытия месяца (D)",
        "Price is inside the active Monthly Open W range": "Цена внутри активного диапазона открытия месяца (W)",
        "Price is inside the active Weekly Open 4H range": "Цена внутри активного диапазона открытия недели (4H)",
        "Price is inside the active Weekly Open D range": "Цена внутри активного диапазона открытия недели (D)",
        "Price is above Monthly Open D range with low raid (+1.0)": "Цена выше диапазона открытия месяца (D) с рейдом снизу (+1.0)",
        "Price is above Monthly Open W range with low raid (+1.0)": "Цена выше диапазона открытия месяца (W) с рейдом снизу (+1.0)",
        "Price is above Monthly Open D range (clean open target, -0.5)": "Цена выше диапазона открытия месяца (D) (чистая цель открытия, -0.5)",
        "Price is above Monthly Open W range (clean open target, -0.5)": "Цена выше диапазона открытия месяца (W) (чистая цель открытия, -0.5)",
        "Price is below Monthly Open D range with high raid (-1.0)": "Цена ниже диапазона открытия месяца (D) с рейдом сверху (-1.0)",
        "Price is below Monthly Open W range with high raid (-1.0)": "Цена ниже диапазона открытия месяца (W) с рейдом сверху (-1.0)",
        "Price is below Monthly Open D range (clean open target, +0.5)": "Цена ниже диапазона открытия месяца (D) (чистая цель открытия, +0.5)",
        "Price is below Monthly Open W range (clean open target, +0.5)": "Цена ниже диапазона открытия месяца (W) (чистая цель открытия, +0.5)",
        "Price is above Weekly Open 4H range with low raid (+1.0)": "Цена выше диапазона открытия недели (4H) с рейдом снизу (+1.0)",
        "Price is above Weekly Open D range with low raid (+1.0)": "Цена выше диапазона открытия недели (D) с рейдом снизу (+1.0)",
        "Price is above Weekly Open 4H range (clean open target, -0.5)": "Цена выше диапазона открытия недели (4H) (чистая цель открытия, -0.5)",
        "Price is above Weekly Open D range (clean open target, -0.5)": "Цена выше диапазона открытия недели (D) (чистая цель открытия, -0.5)",
        "Price is below Weekly Open 4H range with high raid (-1.0)": "Цена ниже диапазона открытия недели (4H) с рейдом сверху (-1.0)",
        "Price is below Weekly Open D range with high raid (-1.0)": "Цена ниже диапазона открытия недели (D) с рейдом сверху (-1.0)",
        "Price is below Weekly Open 4H range (clean open target, +0.5)": "Цена ниже диапазона открытия недели (4H) (чистая цель открытия, +0.5)",
        "Price is below Weekly Open D range (clean open target, +0.5)": "Цена ниже диапазона открытия недели (D) (чистая цель открытия, +0.5)",

        # Directions
        "Steepening": "Крутеет",
        "Flattening": "Выполаживается",
        "Flat": "Флэт",
        "Rising": "Растет",
        "Falling": "Падает",
        
        # Freshness
        "🟢 Fresh": "🟢 Свежие",
        "🔴 Stale": "🔴 Устаревшие",
        "unknown": "неизвестно",
        "fresh": "свежие",
        "stale": "устаревшие",
    }
}


def t(key: str, lang: str = "en") -> str:
    """Return translation for a static key."""
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))


def ts(text: str, lang: str = "en") -> str:
    """Translate dynamic string (categories, factors, reasons) if mapping exists."""
    if lang == "en":
        return text
    if not text:
        return ""
    # Exact lookup
    mapped = STRING_MAP.get("ru", {}).get(text)
    if mapped:
        return mapped
        
    # Check partial mappings or clean strings
    cleaned = text.strip()
    mapped = STRING_MAP.get("ru", {}).get(cleaned)
    if mapped:
        return mapped
        
    # Fallback to translation of parts if it contains specific words
    for eng_word, ru_word in STRING_MAP["ru"].items():
        if eng_word in text:
            # Replace exactly
            text = text.replace(eng_word, ru_word)
            
    return text


def translate_verdict(verdict: str, lang: str = "en") -> str:
    """Translate verdict labels to Russian if selected."""
    if lang == "en":
        return verdict
    v_lower = verdict.lower()
    if "strong bullish" in v_lower:
        return "Сильное бычье смещение EUR/USD"
    if "strong bearish" in v_lower:
        return "Сильное медвежье смещение EUR/USD"
    if "bullish" in v_lower:
        return "Бычье смещение EUR/USD"
    if "bearish" in v_lower:
        return "Медвежье смещение EUR/USD"
    if "neutral" in v_lower or "mixed" in v_lower:
        return "Нейтральное / Смешанное"
    if "insufficient" in v_lower:
        return "Недостаточно данных"
    return verdict
