#!/usr/bin/env python
# -*- coding: utf-8 -*-

import streamlit as st
import tabula
import pandas as pd
import tempfile
import os
from io import BytesIO
import re
from datetime import datetime

def extract_customer_info(dfs):
    """Extract customer information from the dataframes"""
    customer_name = "Not found"
    order_date = "Not found"
    
    # Look through all dataframes for customer info