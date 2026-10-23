def get_custom_css() -> str:
    return """
    <style>
        .main-header {
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
            padding: 24px 28px;
            border-radius: 12px;
            color: #F8FAFC;
            margin-bottom: 24px;
            border-left: 6px solid #3B82F6;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }
        .main-header h1 {
            color: #FFFFFF;
            font-size: 26px;
            font-weight: 700;
            margin: 0 0 6px 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .main-header p {
            color: #94A3B8;
            font-size: 14px;
            margin: 0;
        }

        .metric-card {
            background: #FFFFFF;
            padding: 16px;
            border-radius: 10px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            text-align: center;
        }
        .metric-card-title {
            font-size: 13px;
            font-weight: 600;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .metric-card-val {
            font-size: 28px;
            font-weight: 700;
            margin: 6px 0;
        }

        .badge-studying {
            background-color: #DCFCE7;
            color: #166534;
            padding: 4px 10px;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 12px;
        }
        .badge-distracted {
            background-color: #FFEDD5;
            color: #9A3412;
            padding: 4px 10px;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 12px;
        }
        .badge-indiscipline {
            background-color: #FEE2E2;
            color: #991B1B;
            padding: 4px 10px;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 12px;
        }

        .parent-notice-box {
            background: #FFFBEB;
            border: 1px solid #FCD34D;
            border-left: 5px solid #F59E0B;
            border-radius: 8px;
            padding: 16px;
            margin-top: 15px;
        }
    </style>
    """
