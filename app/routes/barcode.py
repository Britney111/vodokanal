# -*- coding: utf-8 -*-
from flask import Blueprint, render_template
from flask_login import login_required

barcode_bp = Blueprint('barcode', __name__)


@barcode_bp.route('/')
@login_required
def scanner():
    """Страница сканера штрихкодов"""
    return render_template('barcode/scanner.html')
