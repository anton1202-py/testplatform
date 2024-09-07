import logging
import traceback

import telegram
from django.db.models import Count, Q

from analyticalplatform.settings import ADMINS_CHATID_LIST, TELEGRAM_TOKEN
from core.models import User
from unit_economics.models import (MarketplaceCategory, MarketplaceCommission,
                                   MarketplaceLogistic, MarketplaceProduct,
                                   MarketplaceProductPriceWithProfitability,
                                   ProductCostPrice,
                                   ProductForMarketplacePrice,
                                   ProductOzonPrice, ProductPrice,
                                   ProfitabilityMarketplaceProduct)

logger = logging.getLogger(__name__)
