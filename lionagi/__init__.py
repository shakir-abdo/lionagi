"""   
Copyright 2023 HaiyangLi <ocean@lionagi.ai>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import logging
from .version import __version__
from dotenv import load_dotenv

from .utils import *
from .schema.base_schema import *
from .structures import *
from .api_service import *
from .tools import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
load_dotenv()