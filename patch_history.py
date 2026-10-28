from pathlib import Path

p = Path("crmapp/views.py")
s = p.read_text(encoding="utf-8")
marker = '            context["customer_invoices"] = customer_invoices\n'
insert = marker + '''
            from crmapp.models import service_management
            context["service_activity"] = list(
                service_management.objects.filter(
                    customer_id=selected_customer.id
                ).values(
                    "id", "service_date", "service_subject",
                    "contract_status", "contract_type"
                ).order_by("-service_date")
            )
'''
if 'context["service_activity"]' not in s:
    if marker not in s:
        raise SystemExit("View insertion point not found; no changes made.")
    p.write_text(s.replace(marker, insert, 1), encoding="utf-8")

p = Path("templates/product_recommendations.html")
s = p.read_text(encoding="utf-8")
marker = '''    </section>
</div>
{% endif %}'''
insert = '''    </section>

    <section class="ci-section">
        <div class="ci-section-head">
            <h3>Service Activity</h3>
            <p>Recorded services, including services without product entries</p>
        </div>
        {% if service_activity %}
        <div class="ci-table-wrap">
            <table class="ci-table">
                <thead><tr><th>Service ID</th><th>Date</th><th>Subject</th><th>Contract</th><th>Status</th></tr></thead>
                <tbody>
                {% for service in service_activity %}
                    <tr>
                        <td>{{ service.id }}</td>
                        <td>{{ service.service_date|default:"—" }}</td>
                        <td>{{ service.service_subject|default:"Service record" }}</td>
                        <td>{{ service.contract_type|default:"—" }}</td>
                        <td>{{ service.contract_status|default:"—" }}</td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <div class="ci-empty">No service activity recorded for this customer.</div>
        {% endif %}
    </section>
</div>
{% endif %}'''
if "Recorded services, including services without product entries" not in s:
    if marker not in s:
        raise SystemExit("Template insertion point not found; view may already be updated.")
    p.write_text(s.replace(marker, insert, 1), encoding="utf-8")

print("Added separate Service Activity section.")
