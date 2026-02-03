#!/usr/bin/env python3
"""
Generate fin-characteristics.liquid block from Shopify metaobject definition.
Run by GitHub Action hourly, or manually.

Only generates the block if the fin_characteristics metaobject definition exists.
The block only renders on products that have the metaobject reference.
"""
import requests
import os
from datetime import datetime

SHOP_URL = "7aa0b1-14.myshopify.com"
API_VERSION = "2024-01"
ACCESS_TOKEN = os.environ.get('SHOPIFY_ADMIN_TOKEN')
THEME_FILE = "blocks/fin-characteristics.liquid"

if not ACCESS_TOKEN:
    print("No SHOPIFY_ADMIN_TOKEN set, skipping")
    exit(0)

url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/graphql.json"
headers = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

# Check if fin_characteristics metaobject definition exists
query = """
{
  metaobjectDefinitionByType(type: "fin_characteristics") {
    id
    type
    name
    fieldDefinitions {
      key
      name
      type { name }
    }
  }
}
"""

response = requests.post(url, json={"query": query}, headers=headers)

if response.status_code != 200:
    print(f"API error: {response.status_code}")
    exit(1)

data = response.json()
definition = data.get('data', {}).get('metaobjectDefinitionByType')

if not definition:
    print("fin_characteristics metaobject definition not found, skipping")
    exit(0)

fields = definition.get('fieldDefinitions', [])
print(f"Found fin_characteristics with {len(fields)} fields")

timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

liquid = '''{% comment %}
  FIN CHARACTERISTICS - AUTO-GENERATED
  =====================================
  Generated: ''' + timestamp + '''
  Metaobject: fin_characteristics
  Fields: ''' + str(len(fields)) + '''

  DO NOT EDIT - This file is auto-generated from Shopify metaobject definitions.
  Only renders if product has custom.fin_characteristics metaobject reference.
{% endcomment %}

{% liquid
  assign product = closest.product
  if product == blank and request.visual_preview_mode
    assign product = collections.all.products.first
  endif
  assign fin = product.metafields.custom.fin_characteristics.value
%}

{% if fin != blank %}
<div class="fin-characteristics" {{ block.shopify_attributes }}>
  {% if block.settings.show_heading and block.settings.heading != blank %}
    <h3 class="fin-characteristics__heading {{ block.settings.heading_size }}">
      {{ block.settings.heading }}
    </h3>
  {% endif %}

  <div class="fin-characteristics__chart">
    <h4 class="fin-characteristics__title">{{ product.title }}</h4>

    {% comment %} Rake Bar {% endcomment %}
    {% if fin.rake.value != blank %}
    <div class="fin-characteristics__bar-group">
      <div class="fin-characteristics__bar">
        <div class="fin-characteristics__marker" style="left: {{ fin.rake.value }}%;"></div>
      </div>
      <div class="fin-characteristics__labels">
        <span class="fin-characteristics__label-left">
          <span class="fin-characteristics__label-primary">Upright</span> Tight Turns
        </span>
        <span class="fin-characteristics__label-right">
          <span class="fin-characteristics__label-primary">Raked</span> Drawn-Out Turns
        </span>
      </div>
    </div>
    {% endif %}

    {% comment %} Area Bar {% endcomment %}
    {% if fin.area.value != blank %}
    <div class="fin-characteristics__bar-group">
      <div class="fin-characteristics__bar">
        <div class="fin-characteristics__marker" style="left: {{ fin.area.value }}%;"></div>
      </div>
      <div class="fin-characteristics__labels">
        <span class="fin-characteristics__label-left">
          <span class="fin-characteristics__label-primary">Less Area</span> Loose
        </span>
        <span class="fin-characteristics__label-right">
          <span class="fin-characteristics__label-primary">More Area</span> Stable
        </span>
      </div>
    </div>
    {% endif %}

    {% comment %} Speed Bar {% endcomment %}
    {% if fin.speed.value != blank %}
    <div class="fin-characteristics__bar-group">
      <div class="fin-characteristics__bar">
        <div class="fin-characteristics__marker" style="left: {{ fin.speed.value }}%;"></div>
      </div>
      <div class="fin-characteristics__labels">
        <span class="fin-characteristics__label-left">
          <span class="fin-characteristics__label-primary">Speed Control</span>
        </span>
        <span class="fin-characteristics__label-right">
          <span class="fin-characteristics__label-primary">Speed Generating</span> Drive
        </span>
      </div>
    </div>
    {% endif %}

    {% comment %} Flex Bar {% endcomment %}
    {% if fin.flex.value != blank %}
    <div class="fin-characteristics__bar-group">
      <div class="fin-characteristics__bar">
        <div class="fin-characteristics__marker" style="left: {{ fin.flex.value }}%;"></div>
      </div>
      <div class="fin-characteristics__labels">
        <span class="fin-characteristics__label-left">
          <span class="fin-characteristics__label-primary">Less Flex</span> Responsive
        </span>
        <span class="fin-characteristics__label-right">
          <span class="fin-characteristics__label-primary">More Flex</span> Projection
        </span>
      </div>
    </div>
    {% endif %}
  </div>

  {% comment %} Text descriptions {% endcomment %}
  <div class="fin-characteristics__descriptions">
    {% if fin.form_text.value != blank %}
      <div class="fin-characteristics__description">
        <span class="fin-characteristics__description-label">Form |</span>
        {{ fin.form_text.value }}
      </div>
    {% endif %}

    {% if fin.function_text.value != blank %}
      <div class="fin-characteristics__description">
        <span class="fin-characteristics__description-label">Function |</span>
        {{ fin.function_text.value }}
      </div>
    {% endif %}

    {% if fin.feel_text.value != blank %}
      <div class="fin-characteristics__description">
        <span class="fin-characteristics__description-label">Feel |</span>
        {{ fin.feel_text.value }}
      </div>
    {% endif %}

    {% if fin.overall_text.value != blank %}
      <div class="fin-characteristics__description">
        <span class="fin-characteristics__description-label">Overall |</span>
        {{ fin.overall_text.value }}
      </div>
    {% endif %}
  </div>
</div>
{% endif %}

{% stylesheet %}
  .fin-characteristics { width: 100%; }
  .fin-characteristics__heading { margin-bottom: var(--margin-sm); }
  .fin-characteristics__chart { margin-bottom: var(--margin-md); }
  .fin-characteristics__title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    margin-bottom: var(--margin-sm);
  }
  .fin-characteristics__bar-group { margin-bottom: 0.75rem; }
  .fin-characteristics__bar {
    position: relative;
    height: 12px;
    border: 1px solid #898989;
    background: transparent;
  }
  .fin-characteristics__marker {
    position: absolute;
    top: 0;
    width: 5px;
    height: 100%;
    background: #A82E2D;
    transform: translateX(-50%);
  }
  .fin-characteristics__labels {
    display: flex;
    justify-content: space-between;
    margin-top: 0.25rem;
    font-size: 0.75rem;
    color: #898989;
  }
  .fin-characteristics__label-primary {
    color: rgb(var(--color-foreground-rgb));
    font-weight: var(--font-weight-medium);
  }
  .fin-characteristics__descriptions {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .fin-characteristics__description {
    font-size: var(--font-size-sm);
    line-height: 1.4;
  }
  .fin-characteristics__description-label {
    font-weight: var(--font-weight-bold);
    text-transform: uppercase;
    margin-right: 0.25rem;
  }
{% endstylesheet %}

{% schema %}
{
  "name": "Fin characteristics",
  "tag": null,
  "settings": [
    { "type": "paragraph", "content": "Auto-generated. Only shows on products with fin_characteristics metaobject." },
    { "type": "checkbox", "id": "show_heading", "label": "Show heading", "default": true },
    { "type": "text", "id": "heading", "label": "Heading", "default": "Form, Function & Feel" },
    { "type": "select", "id": "heading_size", "label": "Heading size", "options": [
      { "value": "h4", "label": "Small" },
      { "value": "h3", "label": "Medium" },
      { "value": "h2", "label": "Large" }
    ], "default": "h4" },
    { "type": "range", "id": "padding-block-start", "label": "Top padding", "min": 0, "max": 100, "step": 1, "unit": "px", "default": 16 },
    { "type": "range", "id": "padding-block-end", "label": "Bottom padding", "min": 0, "max": 100, "step": 1, "unit": "px", "default": 16 }
  ],
  "presets": [{ "name": "Fin characteristics", "category": "Product" }]
}
{% endschema %}'''

with open(THEME_FILE, 'w') as f:
    f.write(liquid)

print(f"Generated {THEME_FILE}")
