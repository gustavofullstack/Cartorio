from app.services.chatwoot_canned_responses import CANNED_RESPONSES
import timeit
setup = 'from app.services.chatwoot_canned_responses import get_by_short_code'
print(timeit.timeit('get_by_short_code("certidao_teor")', setup=setup, number=100000))
