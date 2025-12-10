# MORDZIX API – manifest endpointów

- Root projektu: `/root/mordzix-ai`
- Łącznie endpointów /api/*: **155**

## Grupa: `admin`  (5 endpointów)

- `POST      ` `/api/admin/cache/clear`  _(legacy_root_py.admin_endpoint.clear_cache)_
- `GET       ` `/api/admin/cache/stats`  _(legacy_root_py.admin_endpoint.cache_stats)_
- `POST      ` `/api/admin/jwt/rotate`  _(legacy_root_py.admin_endpoint.admin_rotate_jwt)_
- `GET       ` `/api/admin/ratelimit/config`  _(legacy_root_py.admin_endpoint.rate_limit_config)_
- `GET       ` `/api/admin/ratelimit/usage/{user_id}`  _(legacy_root_py.admin_endpoint.rate_limit_usage)_

## Grupa: `automation`  (1 endpointów)

- `GET       ` `/api/automation/status`  _(core.app.automation_status)_

## Grupa: `autoroute`  (4 endpointów)

- `POST      ` `/api/autoroute/analyze`  _(core.frontend_autorouter.analyze_route; tags: autorouter)_
- `GET       ` `/api/autoroute/endpoints`  _(core.frontend_autorouter.get_available_endpoints; tags: autorouter)_
- `POST      ` `/api/autoroute/execute`  _(core.frontend_autorouter.execute_route; tags: autorouter)_
- `GET       ` `/api/autoroute/stats`  _(core.frontend_autorouter.get_routing_stats; tags: autorouter)_

## Grupa: `batch`  (4 endpointów)

- `GET       ` `/api/batch/metrics`  _(core.batch_endpoint.batch_metrics_endpoint; tags: LLM Batch Processing)_
- `POST      ` `/api/batch/process`  _(core.batch_endpoint.batch_process_endpoint; tags: LLM Batch Processing)_
- `POST      ` `/api/batch/shutdown`  _(core.batch_endpoint.batch_shutdown_endpoint; tags: LLM Batch Processing)_
- `POST      ` `/api/batch/submit`  _(core.batch_endpoint.batch_submit_endpoint; tags: LLM Batch Processing)_

## Grupa: `captcha`  (2 endpointów)

- `GET       ` `/api/captcha/balance`  _(legacy_root_py.captcha_endpoint.get_balance; tags: captcha)_
- `POST      ` `/api/captcha/solve`  _(legacy_root_py.captcha_endpoint.solve_captcha; tags: captcha)_

## Grupa: `chat`  (3 endpointów)

- `POST      ` `/api/chat/assistant`  _(core.assistant_endpoint.chat_assistant)_
- `POST      ` `/api/chat/assistant/stream`  _(core.assistant_endpoint.chat_assistant_stream)_
- `POST      ` `/api/chat/auto`  _(core.assistant_endpoint.force_auto_learn)_

## Grupa: `code`  (14 endpointów)

- `POST      ` `/api/code/deps/install`  _(legacy_root_py.programista_endpoint.deps_install)_
- `POST      ` `/api/code/docker/build`  _(legacy_root_py.programista_endpoint.docker_build)_
- `POST      ` `/api/code/docker/run`  _(legacy_root_py.programista_endpoint.docker_run)_
- `POST      ` `/api/code/exec`  _(legacy_root_py.programista_endpoint.exec_command)_
- `POST      ` `/api/code/format`  _(legacy_root_py.programista_endpoint.format_code)_
- `POST      ` `/api/code/git`  _(legacy_root_py.programista_endpoint.git)_
- `POST      ` `/api/code/init`  _(legacy_root_py.programista_endpoint.project_init)_
- `POST      ` `/api/code/lint`  _(legacy_root_py.programista_endpoint.lint)_
- `POST      ` `/api/code/plan`  _(legacy_root_py.programista_endpoint.plan)_
- `GET       ` `/api/code/read`  _(legacy_root_py.programista_endpoint.read_file)_
- `GET       ` `/api/code/snapshot`  _(legacy_root_py.programista_endpoint.snapshot)_
- `POST      ` `/api/code/test`  _(legacy_root_py.programista_endpoint.test)_
- `GET       ` `/api/code/tree`  _(legacy_root_py.programista_endpoint.read_tree)_
- `POST      ` `/api/code/write`  _(legacy_root_py.programista_endpoint.write_file)_

## Grupa: `cognitive`  (10 endpointów)

- `POST      ` `/api/cognitive/nlp/analyze`  _(core.cognitive_endpoint.nlp_advanced_analysis; tags: cognitive)_
- `POST      ` `/api/cognitive/proactive/suggestions`  _(core.cognitive_endpoint.generate_proactive_suggestions; tags: cognitive)_
- `POST      ` `/api/cognitive/process`  _(core.cognitive_endpoint.cognitive_process; tags: cognitive)_
- `POST      ` `/api/cognitive/psychology/analyze`  _(core.cognitive_endpoint.analyze_emotional_state; tags: cognitive)_
- `GET       ` `/api/cognitive/psychology/state/{user_id}`  _(core.cognitive_endpoint.get_psychology_state; tags: cognitive)_
- `POST      ` `/api/cognitive/reflect`  _(core.cognitive_endpoint.self_reflect; tags: cognitive)_
- `GET       ` `/api/cognitive/reflection/summary`  _(core.cognitive_endpoint.get_reflection_summary; tags: cognitive)_
- `POST      ` `/api/cognitive/semantic/analyze`  _(core.cognitive_endpoint.semantic_analysis; tags: cognitive)_
- `GET       ` `/api/cognitive/status`  _(core.cognitive_endpoint.cognitive_status; tags: cognitive)_
- `GET       ` `/api/cognitive/tools/list`  _(core.cognitive_endpoint.list_cognitive_tools; tags: cognitive)_

## Grupa: `endpoints`  (1 endpointów)

- `GET       ` `/api/endpoints/list`  _(core.app.list_endpoints)_

## Grupa: `fashion`  (7 endpointów)

- `GET       ` `/api/fashion/categories`  _(legacy_root_py.fashion_endpoint.get_fashion_categories; tags: AI Fashion)_
- `POST      ` `/api/fashion/detect-brand`  _(legacy_root_py.fashion_endpoint.detect_brand; tags: AI Fashion)_
- `POST      ` `/api/fashion/forecast-trends`  _(legacy_root_py.fashion_endpoint.forecast_trends; tags: AI Fashion)_
- `POST      ` `/api/fashion/generate-outfit`  _(legacy_root_py.fashion_endpoint.generate_outfit; tags: AI Fashion)_
- `GET       ` `/api/fashion/occasions`  _(legacy_root_py.fashion_endpoint.get_occasions; tags: AI Fashion)_
- `GET       ` `/api/fashion/stats`  _(legacy_root_py.fashion_endpoint.get_fashion_stats; tags: AI Fashion)_
- `GET       ` `/api/fashion/weather-types`  _(legacy_root_py.fashion_endpoint.get_weather_types; tags: AI Fashion)_

## Grupa: `ff`  (1 endpointów)

- `POST      ` `/api/ff/proxy`  _(legacy_root_py.ff_sidecar.proxy; tags: ff-proxy)_

## Grupa: `files`  (11 endpointów)

- `POST      ` `/api/files/analyze`  _(legacy_root_py.files_endpoint.analyze_file)_
- `POST      ` `/api/files/batch/analyze`  _(legacy_root_py.files_endpoint.batch_analyze)_
- `POST      ` `/api/files/delete`  _(legacy_root_py.files_endpoint.delete_file)_
- `GET       ` `/api/files/download`  _(legacy_root_py.files_endpoint.download_file)_
- `GET       ` `/api/files/list`  _(legacy_root_py.files_endpoint.list_files)_
- `GET       ` `/api/files/stats`  _(legacy_root_py.files_endpoint.files_stats)_
- `GET       ` `/api/files/thumb/{tenant}/{day}/{name}`  _(core.files_endpoint.thumb; tags: files)_
- `POST      ` `/api/files/upload`  _(core.files_endpoint.upload; tags: files)_
- `POST      ` `/api/files/upload`  _(legacy_root_py.files_endpoint.upload_file)_
- `POST      ` `/api/files/upload/base64`  _(legacy_root_py.files_endpoint.upload_base64)_
- `GET       ` `/api/files/{tenant}/{day}/{name}`  _(core.files_endpoint.download; tags: files)_

## Grupa: `hacker`  (6 endpointów)

- `POST      ` `/api/hacker/exploit/sqli`  _(legacy_root_py.hacker_endpoint.sql_injection_scanner; tags: AI Hacker Assistant)_
- `GET       ` `/api/hacker/exploits/list`  _(legacy_root_py.hacker_endpoint.list_exploit_modules; tags: AI Hacker Assistant)_
- `POST      ` `/api/hacker/recon/domain`  _(legacy_root_py.hacker_endpoint.domain_reconnaissance; tags: AI Hacker Assistant)_
- `POST      ` `/api/hacker/scan/ports`  _(legacy_root_py.hacker_endpoint.network_scan; tags: AI Hacker Assistant)_
- `POST      ` `/api/hacker/scan/vulnerabilities`  _(legacy_root_py.hacker_endpoint.vulnerability_scanner; tags: AI Hacker Assistant)_
- `GET       ` `/api/hacker/tools/status`  _(legacy_root_py.hacker_endpoint.hacker_tools_status; tags: AI Hacker Assistant)_

## Grupa: `image`  (2 endpointów)

- `GET       ` `/api/image/file/{tenant}/{name}`  _(core.image_endpoint.image_file; tags: image)_
- `POST      ` `/api/image/generate`  _(core.image_endpoint.generate; tags: image)_

## Grupa: `internal`  (2 endpointów)

- `GET       ` `/api/internal/ui`  _(legacy_root_py.internal_ui.ui_info)_
- `GET       ` `/api/internal/ui_token`  _(legacy_root_py.internal_endpoint.ui_token)_

## Grupa: `lang`  (1 endpointów)

- `POST      ` `/api/lang/detect`  _(core.lang_endpoint.detect; tags: lang)_

## Grupa: `memory`  (6 endpointów)

- `POST      ` `/api/memory/add`  _(core.memory_endpoint.add; tags: memory)_
- `GET       ` `/api/memory/export`  _(core.memory_endpoint.export; tags: memory)_
- `POST      ` `/api/memory/import`  _(core.memory_endpoint.import_; tags: memory)_
- `POST      ` `/api/memory/optimize`  _(core.memory_endpoint.optimize; tags: memory)_
- `POST      ` `/api/memory/search`  _(core.memory_endpoint.search; tags: memory)_
- `GET       ` `/api/memory/status`  _(core.memory_endpoint.status; tags: memory)_

## Grupa: `ml`  (5 endpointów)

- `GET       ` `/api/ml/model-info`  _(legacy_root_py.ml_endpoint.get_model_info; tags: Machine Learning)_
- `POST      ` `/api/ml/predict-suggestions`  _(legacy_root_py.ml_endpoint.predict_suggestions; tags: Machine Learning)_
- `POST      ` `/api/ml/record-feedback`  _(legacy_root_py.ml_endpoint.record_feedback; tags: Machine Learning)_
- `POST      ` `/api/ml/retrain`  _(legacy_root_py.ml_endpoint.retrain_model; tags: Machine Learning)_
- `GET       ` `/api/ml/stats`  _(legacy_root_py.ml_endpoint.get_stats; tags: Machine Learning)_

## Grupa: `nlp`  (8 endpointów)

- `POST      ` `/api/nlp/analyze`  _(legacy_root_py.nlp_endpoint.analyze_text; tags: nlp)_
- `POST      ` `/api/nlp/batch-analyze`  _(legacy_root_py.nlp_endpoint.batch_analyze_texts; tags: nlp)_
- `POST      ` `/api/nlp/entities`  _(legacy_root_py.nlp_endpoint.extract_entities; tags: nlp)_
- `POST      ` `/api/nlp/extract-topics`  _(legacy_root_py.nlp_endpoint.extract_topics; tags: nlp)_
- `POST      ` `/api/nlp/key-phrases`  _(legacy_root_py.nlp_endpoint.extract_key_phrases; tags: nlp)_
- `POST      ` `/api/nlp/readability`  _(legacy_root_py.nlp_endpoint.calculate_readability; tags: nlp)_
- `POST      ` `/api/nlp/sentiment`  _(legacy_root_py.nlp_endpoint.analyze_sentiment; tags: nlp)_
- `GET       ` `/api/nlp/stats`  _(legacy_root_py.nlp_endpoint.get_nlp_stats; tags: nlp)_

## Grupa: `prometheus`  (3 endpointów)

- `GET       ` `/api/prometheus/health`  _(core.prometheus_endpoint.health_check; tags: monitoring)_
- `GET       ` `/api/prometheus/metrics`  _(core.prometheus_endpoint.get_prometheus_metrics; tags: monitoring)_
- `GET       ` `/api/prometheus/stats`  _(core.prometheus_endpoint.get_stats; tags: monitoring)_

## Grupa: `psyche`  (5 endpointów)

- `POST      ` `/api/psyche`  _(core.psyche_endpoint.psyche_analyze; tags: psyche)_
- `GET       ` `/api/psyche/history`  _(core.psyche_endpoint.psyche_history; tags: psyche)_
- `POST      ` `/api/psyche/reset`  _(core.psyche_endpoint.psyche_reset; tags: psyche)_
- `GET       ` `/api/psyche/state`  _(core.psyche_endpoint.psyche_state; tags: psyche)_
- `POST      ` `/api/psyche/state`  _(core.psyche_endpoint.psyche_state_set; tags: psyche)_

## Grupa: `research`  (4 endpointów)

- `POST      ` `/api/research/autonauka`  _(legacy_root_py.research_endpoint.run_autonauka; tags: research)_
- `POST      ` `/api/research/search`  _(legacy_root_py.research_endpoint.web_search; tags: research)_
- `GET       ` `/api/research/sources`  _(legacy_root_py.research_endpoint.available_sources; tags: research)_
- `GET       ` `/api/research/test`  _(legacy_root_py.research_endpoint.test_research; tags: research)_

## Grupa: `search`  (5 endpointów)

- `POST      ` `/api/search/compare`  _(core.hybrid_search_endpoint.compare_methods)_
- `POST      ` `/api/search/hybrid`  _(core.hybrid_search_endpoint.hybrid_search)_
- `GET       ` `/api/search/stats`  _(core.hybrid_search_endpoint.search_stats)_
- `GET       ` `/api/search/test`  _(core.hybrid_search_endpoint.test_search)_
- `GET       ` `/api/search/widget`  _(core.hybrid_search_endpoint.search_widget)_

## Grupa: `stt`  (4 endpointów)

- `GET       ` `/api/stt/file/{tenant}/{name}`  _(core.stt_endpoint.stt_file; tags: stt)_
- `GET       ` `/api/stt/providers`  _(legacy_root_py.stt_endpoint.list_stt_providers; tags: speech)_
- `POST      ` `/api/stt/transcribe`  _(core.stt_endpoint.transcribe; tags: stt)_
- `POST      ` `/api/stt/transcribe`  _(legacy_root_py.stt_endpoint.transcribe_audio; tags: speech)_

## Grupa: `suggestions`  (4 endpointów)

- `POST      ` `/api/suggestions/analyze`  _(core.suggestions_endpoint.analyze_message; tags: Proactive Suggestions)_
- `POST      ` `/api/suggestions/generate`  _(core.suggestions_endpoint.generate_suggestions; tags: Proactive Suggestions)_
- `POST      ` `/api/suggestions/inject`  _(core.suggestions_endpoint.inject_suggestions; tags: Proactive Suggestions)_
- `GET       ` `/api/suggestions/stats`  _(core.suggestions_endpoint.get_stats; tags: Proactive Suggestions)_

## Grupa: `travel`  (6 endpointów)

- `GET       ` `/api/travel/attractions/{city}`  _(core.travel_endpoint.get_attractions)_
- `GET       ` `/api/travel/geocode`  _(core.travel_endpoint.geocode_city)_
- `GET       ` `/api/travel/hotels/{city}`  _(core.travel_endpoint.get_hotels)_
- `GET       ` `/api/travel/restaurants/{city}`  _(core.travel_endpoint.get_restaurants)_
- `GET       ` `/api/travel/search`  _(core.travel_endpoint.search_travel)_
- `GET       ` `/api/travel/trip-plan`  _(core.travel_endpoint.plan_trip)_

## Grupa: `tts`  (2 endpointów)

- `POST      ` `/api/tts/speak`  _(legacy_root_py.tts_endpoint.speak; tags: tts)_
- `GET       ` `/api/tts/voices`  _(legacy_root_py.tts_endpoint.list_voices; tags: tts)_

## Grupa: `vision`  (2 endpointów)

- `POST      ` `/api/vision/describe`  _(core.vision_endpoint.describe; tags: vision)_
- `POST      ` `/api/vision/ocr`  _(core.vision_endpoint.ocr; tags: vision)_

## Grupa: `voice`  (2 endpointów)

- `GET       ` `/api/voice/file/{tenant}/{name}`  _(core.voice_endpoint.voice_file; tags: voice)_
- `POST      ` `/api/voice/tts`  _(core.voice_endpoint.tts; tags: voice)_

## Grupa: `writer`  (13 endpointów)

- `POST      ` `/api/writer/article/masterpiece`  _(legacy_root_py.writer_pro.create_masterpiece_article; tags: writing)_
- `GET       ` `/api/writer/auction/knowledge`  _(legacy_root_py.writer_pro.get_auction_knowledge; tags: writing)_
- `POST      ` `/api/writer/auction/learn`  _(legacy_root_py.writer_pro.learn_auction_knowledge; tags: writing)_
- `POST      ` `/api/writer/auction/pro`  _(legacy_root_py.writer_pro.create_auction_pro_description; tags: writing)_
- `GET       ` `/api/writer/auction/tags`  _(legacy_root_py.writer_pro.get_auction_tags; tags: writing)_
- `POST      ` `/api/writer/creative`  _(legacy_root_py.writer_pro.create_creative_text; tags: writing)_
- `POST      ` `/api/writer/fashion/analyze`  _(legacy_root_py.writer_pro.analyze_fashion_content; tags: writing)_
- `POST      ` `/api/writer/product`  _(legacy_root_py.writer_pro.create_product_description; tags: writing)_
- `POST      ` `/api/writer/sales/masterpiece`  _(legacy_root_py.writer_pro.create_sales_masterpiece; tags: writing)_
- `POST      ` `/api/writer/social`  _(legacy_root_py.writer_pro.create_social_media_post; tags: writing)_
- `GET       ` `/api/writer/status`  _(legacy_root_py.writer_pro.get_writer_status; tags: writing)_
- `POST      ` `/api/writer/technical/masterpiece`  _(legacy_root_py.writer_pro.create_technical_masterpiece; tags: writing)_
- `GET       ` `/api/writer/templates`  _(legacy_root_py.writer_pro.get_writing_templates; tags: writing)_

## Grupa: `writing`  (12 endpointów)

- `POST      ` `/api/writing/auction`  _(legacy_root_py.writing_endpoint.auction_description)_
- `GET       ` `/api/writing/auction/kb/fetch`  _(legacy_root_py.writing_endpoint.fetch_auction_kb)_
- `POST      ` `/api/writing/auction/kb/learn`  _(legacy_root_py.writing_endpoint.learn_auction_kb)_
- `POST      ` `/api/writing/auction/pro`  _(legacy_root_py.writing_endpoint.auction_pro_description)_
- `POST      ` `/api/writing/auction/suggest-tags`  _(legacy_root_py.writing_endpoint.suggest_auction_tags)_
- `POST      ` `/api/writing/creative`  _(legacy_root_py.writing_endpoint.creative_writing)_
- `POST      ` `/api/writing/fashion/analyze`  _(legacy_root_py.writing_endpoint.fashion_analysis)_
- `POST      ` `/api/writing/masterpiece/article`  _(legacy_root_py.writing_endpoint.masterpiece_article)_
- `POST      ` `/api/writing/masterpiece/sales`  _(legacy_root_py.writing_endpoint.sales_masterpiece)_
- `POST      ` `/api/writing/masterpiece/technical`  _(legacy_root_py.writing_endpoint.technical_masterpiece)_
- `POST      ` `/api/writing/social`  _(legacy_root_py.writing_endpoint.social_media_post)_
- `POST      ` `/api/writing/vinted`  _(legacy_root_py.writing_endpoint.vinted_description)_
