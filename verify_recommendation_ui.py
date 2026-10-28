exec(open("verify_recommendation_view.py", encoding="utf-8-sig").read().replace(
    'print("Error:", context.get("error_message"))',
    '''
            html = response.content.decode("utf-8")
            print("History table visible:", "purchase-history-table" in html)
            print("Recommendation results visible:", "recommendation(s) returned" in html)
            print("No-recommendations message visible:", "Purchase history found, but no eligible cross-sell recommendations" in html)
            print("No-history message visible:", "No recorded service-product purchase history" in html)
            print("Error:", context.get("error_message"))
    '''
))
