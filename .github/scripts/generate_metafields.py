#!/usr/bin/env python3
"""
Generate product-metafields.liquid from Shopify metafield definitions.
Run by GitHub Action hourly, or manually.

Automatically includes visualizations for any metaobject references found on products.
- Integer fields (0-100) render as progress bars
- Text fields render as labeled descriptions
- Scales to any metaobject type without code changes
"""
import requests
import os
from datetime import datetime

SHOP_URL = "7aa0b1-14.myshopify.com"
API_VERSION = "2024-01"
ACCESS_TOKEN = os.environ.get('SHOPIFY_ADMIN_TOKEN')
THEME_FILE = "blocks/product-metafields.liquid"

INCLUDE_NAMESPACES = ['custom', 'gato_heroi', 'reviews', 'descriptors']
EXCLUDE_KEYS = ['rating_value', 'review_count', 'rating', 'rating_count', 'availability']

# Bar field configurations: define left/right labels and icons for each field
# Format: 'metaobject_type.field_key': { left_label, right_label, left_icon, right_icon }
BAR_FIELD_CONFIG = {
    'fin_characteristics.rake': {
        'left_label': 'Upright',
        'left_sublabel': 'Tight Turns',
        'right_label': 'Raked',
        'right_sublabel': 'Drawn-Out Turns',
        'left_icon': 'icon-fin-upright.svg',
        'right_icon': 'icon-fin-raked.svg'
    },
    'fin_characteristics.area': {
        'left_label': 'Less Area',
        'left_sublabel': 'Loose',
        'right_label': 'More Area',
        'right_sublabel': 'Stable',
        'left_icon': 'icon-fin-less-area.svg',
        'right_icon': 'icon-fin-more-area.svg'
    },
    'fin_characteristics.speed': {
        'left_label': 'Speed Control',
        'left_sublabel': '',
        'right_label': 'Speed Generating',
        'right_sublabel': 'Drive',
        'left_icon': 'icon-fin-speed-control.svg',
        'right_icon': 'icon-fin-speed-drive.svg'
    },
    'fin_characteristics.flex': {
        'left_label': 'Less Flex',
        'left_sublabel': 'Responsive',
        'right_label': 'More Flex',
        'right_sublabel': 'Projection',
        'left_icon': 'icon-fin-less-flex.svg',
        'right_icon': 'icon-fin-more-flex.svg'
    }
}

if not ACCESS_TOKEN:
    print("No SHOPIFY_ADMIN_TOKEN set, skipping")
    exit(0)

url = f"https://{SHOP_URL}/admin/api/{API_VERSION}/graphql.json"
headers = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

# Get all product metafield definitions
query = """
{
  metafieldDefinitions(ownerType: PRODUCT, first: 100) {
    edges {
      node {
        namespace
        key
        name
        type { name }
      }
    }
  }
}
"""

response = requests.post(url, json={"query": query}, headers=headers)
if response.status_code != 200:
    print(f"API error: {response.status_code}")
    exit(1)

data = response.json()
edges = data.get('data', {}).get('metafieldDefinitions', {}).get('edges', [])

# Separate metaobject references from regular metafields
metaobject_refs = []
regular_fields = []

for e in edges:
    node = e['node']
    ns = node['namespace']
    key = node['key']
    ftype = node['type']['name']

    if ftype == 'metaobject_reference':
        metaobject_refs.append({
            'namespace': ns,
            'key': key,
            'name': node['name']
        })
    elif ns in INCLUDE_NAMESPACES and key not in EXCLUDE_KEYS:
        regular_fields.append({
            'namespace': ns,
            'key': key,
            'name': node['name'],
            'type': ftype
        })

print(f"Found {len(regular_fields)} regular metafields")
print(f"Found {len(metaobject_refs)} metaobject references")

# Get field definitions for each metaobject type
metaobject_definitions = {}
for ref in metaobject_refs:
    # Query the metaobject definition to get its fields
    mo_query = """
    query GetMetaobjectDef($type: String!) {
      metaobjectDefinitionByType(type: $type) {
        type
        name
        fieldDefinitions {
          key
          name
          type { name }
          validations { name value }
        }
      }
    }
    """
    # The metaobject type is typically the key name
    mo_type = ref['key']
    mo_response = requests.post(url, json={"query": mo_query, "variables": {"type": mo_type}}, headers=headers)
    mo_data = mo_response.json()
    definition = mo_data.get('data', {}).get('metaobjectDefinitionByType')

    if definition:
        metaobject_definitions[mo_type] = {
            'namespace': ref['namespace'],
            'key': ref['key'],
            'name': definition['name'],
            'fields': definition['fieldDefinitions']
        }
        print(f"  - {mo_type}: {len(definition['fieldDefinitions'])} fields")

# Generate Liquid for regular metafields
field_blocks = []
for f in regular_fields:
    ns = f['namespace']
    key = f['key']
    name = f['name']
    ftype = f['type']

    if ftype == 'url':
        value_output = '<a href="{{ product.metafields.' + ns + '.' + key + '.value }}" target="_blank">View Guide</a>'
    elif ftype == 'multi_line_text_field':
        value_output = '{{ product.metafields.' + ns + '.' + key + '.value | newline_to_br }}'
    else:
        value_output = '{{ product.metafields.' + ns + '.' + key + '.value }}'

    block = '    {% if product.metafields.' + ns + '.' + key + '.value != blank %}\n'
    block += '      <div class="product-metafields__item">\n'
    block += '        <dt class="product-metafields__label">' + name + '</dt>\n'
    block += '        <dd class="product-metafields__value">' + value_output + '</dd>\n'
    block += '      </div>\n'
    block += '    {% endif %}'
    field_blocks.append(block)

fields_html = '\n'.join(field_blocks)

# Generate Liquid for metaobject visualizations
metaobject_visualizations = []
for mo_type, mo_def in metaobject_definitions.items():
    ns = mo_def['namespace']
    key = mo_def['key']
    name = mo_def['name']
    fields = mo_def['fields']

    # Separate integer fields (for bars) from text fields (for descriptions)
    bar_fields = []
    text_fields = []

    for field in fields:
        field_type = field['type']['name']
        field_key = field['key']
        field_name = field['name']

        # Check validations for min/max (indicates a bar-style field)
        validations = {v['name']: v['value'] for v in field.get('validations', [])}

        if field_type == 'number_integer':
            # Check if it has 0-100 range (bar visualization)
            min_val = validations.get('min', '0')
            max_val = validations.get('max', '100')
            bar_fields.append({
                'key': field_key,
                'name': field_name,
                'min': min_val,
                'max': max_val
            })
        elif field_type in ['single_line_text_field', 'multi_line_text_field']:
            text_fields.append({
                'key': field_key,
                'name': field_name,
                'multiline': field_type == 'multi_line_text_field'
            })

    # Build visualization HTML for this metaobject
    viz_var = f"mo_{key.replace('-', '_')}"

    viz_html = f'''
  {{% assign {viz_var} = product.metafields.{ns}.{key}.value %}}
  {{% if {viz_var} != blank %}}
  <div class="metaobject-viz metaobject-viz--{key}">
    <h4 class="metaobject-viz__title">{name}</h4>
'''

    # Add bar visualizations
    if bar_fields:
        viz_html += '    <div class="metaobject-viz__bars">\n'
        for bf in bar_fields:
            config_key = f"{mo_type}.{bf['key']}"
            config = BAR_FIELD_CONFIG.get(config_key, {})

            left_label = config.get('left_label', bf['name'])
            left_sublabel = config.get('left_sublabel', '')
            right_label = config.get('right_label', '')
            right_sublabel = config.get('right_sublabel', '')
            left_icon = config.get('left_icon', '')
            right_icon = config.get('right_icon', '')

            # Build left side
            left_html = '<span class="metaobject-viz__endpoint metaobject-viz__endpoint--left">'
            if left_icon:
                left_html += f'<span class="metaobject-viz__icon">{{{{ "{left_icon}" | asset_url | split: "?" | first }}}}</span>'
            left_html += f'<span class="metaobject-viz__endpoint-text"><strong>{left_label}</strong>'
            if left_sublabel:
                left_html += f' {left_sublabel}'
            left_html += '</span></span>'

            # Build right side
            right_html = '<span class="metaobject-viz__endpoint metaobject-viz__endpoint--right">'
            right_html += f'<span class="metaobject-viz__endpoint-text"><strong>{right_label}</strong>'
            if right_sublabel:
                right_html += f' {right_sublabel}'
            right_html += '</span>'
            if right_icon:
                right_html += f'<span class="metaobject-viz__icon">{{{{ "{right_icon}" | asset_url | split: "?" | first }}}}</span>'
            right_html += '</span>'

            viz_html += f'''      {{% if {viz_var}.{bf['key']}.value != blank %}}
      <div class="metaobject-viz__bar-group">
        <div class="metaobject-viz__bar-row">
          {left_html}
          <div class="metaobject-viz__bar">
            <div class="metaobject-viz__marker" style="left: {{{{ {viz_var}.{bf['key']}.value }}}}%;"></div>
          </div>
          {right_html}
        </div>
      </div>
      {{% endif %}}
'''
        viz_html += '    </div>\n'

    # Add text descriptions
    if text_fields:
        viz_html += '    <div class="metaobject-viz__descriptions">\n'
        for tf in text_fields:
            # Convert key to label (e.g., form_text -> Form)
            label = tf['name'].replace(' Text', '').replace('_text', '').replace('_', ' ').title()
            value_filter = ' | newline_to_br' if tf['multiline'] else ''
            viz_html += f'''      {{% if {viz_var}.{tf['key']}.value != blank %}}
      <div class="metaobject-viz__description">
        <strong>{label} |</strong> {{{{ {viz_var}.{tf['key']}.value{value_filter} }}}}
      </div>
      {{% endif %}}
'''
        viz_html += '    </div>\n'

    viz_html += f'''  </div>
  {{% endif %}}
'''
    metaobject_visualizations.append(viz_html)

metaobject_html = '\n'.join(metaobject_visualizations)

timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
namespaces_str = ', '.join(INCLUDE_NAMESPACES)
mo_types_str = ', '.join(metaobject_definitions.keys()) if metaobject_definitions else 'none'

liquid = '''{% comment %}
  PRODUCT METAFIELDS - AUTO-GENERATED
  ====================================
  Generated: ''' + timestamp + '''
  Regular fields: ''' + str(len(regular_fields)) + '''
  Metaobject types: ''' + mo_types_str + '''
  Namespaces: ''' + namespaces_str + '''

  DO NOT EDIT - This file is auto-generated from Shopify metafield definitions.

  Metaobject visualizations are automatically generated:
  - Integer fields (0-100) render as progress bars
  - Text fields render as labeled descriptions
{% endcomment %}

{% liquid
  assign product = closest.product
  if product == blank and request.visual_preview_mode
    assign product = collections.all.products.first
  endif
%}

<div class="product-metafields" {{ block.shopify_attributes }}>
  {% if block.settings.show_heading and block.settings.heading != blank %}
    <h3 class="product-metafields__heading {{ block.settings.heading_size }}">
      {{ block.settings.heading }}
    </h3>
  {% endif %}
''' + metaobject_html + '''
  <dl class="product-metafields__list">
''' + fields_html + '''
  </dl>
</div>

{% stylesheet %}
  .product-metafields { width: 100%; }
  .product-metafields__heading { margin-bottom: var(--margin-sm); }
  .product-metafields__list { display: grid; gap: var(--gap-xs); margin: 0; }
  .product-metafields__item {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: var(--gap-md);
    padding: var(--padding-xs) 0;
    border-bottom: 1px solid rgb(var(--color-foreground-rgb) / var(--opacity-10));
  }
  .product-metafields__item:last-child { border-bottom: none; }
  .product-metafields__label {
    font-weight: var(--font-weight-semibold);
    color: rgb(var(--color-foreground-rgb) / var(--opacity-70));
    flex-shrink: 0;
  }
  .product-metafields__value { margin: 0; text-align: right; max-width: 65%; }
  .product-metafields__value a { color: var(--color-primary); text-decoration: underline; }

  /* Metaobject visualizations */
  .metaobject-viz { margin-bottom: var(--margin-lg); padding-bottom: var(--padding-md); border-bottom: 1px solid rgb(var(--color-foreground-rgb) / var(--opacity-10)); }
  .metaobject-viz__title { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); margin-bottom: var(--margin-sm); text-transform: uppercase; letter-spacing: 0.05em; }
  .metaobject-viz__bars { margin-bottom: var(--margin-md); }
  .metaobject-viz__bar-group { margin-bottom: 0.75rem; }
  .metaobject-viz__bar { position: relative; height: 12px; border: 1px solid #898989; background: transparent; }
  .metaobject-viz__marker { position: absolute; top: 0; width: 5px; height: 100%; background: #A82E2D; transform: translateX(-50%); }
  .metaobject-viz__bar-label { margin-top: 0.25rem; font-size: 0.7rem; color: rgb(var(--color-foreground-rgb) / var(--opacity-70)); }
  .metaobject-viz__descriptions { display: flex; flex-direction: column; gap: 0.375rem; font-size: var(--font-size-sm); }
  .metaobject-viz__description strong { text-transform: uppercase; }
{% endstylesheet %}

{% schema %}
{
  "name": "Product specs",
  "tag": null,
  "settings": [
    { "type": "paragraph", "content": "Auto-generated from Shopify metafields and metaobjects." },
    { "type": "checkbox", "id": "show_heading", "label": "Show heading", "default": true },
    { "type": "text", "id": "heading", "label": "Heading", "default": "Specifications" },
    { "type": "select", "id": "heading_size", "label": "Heading size", "options": [
      { "value": "h4", "label": "Small" },
      { "value": "h3", "label": "Medium" },
      { "value": "h2", "label": "Large" }
    ], "default": "h4" },
    { "type": "range", "id": "padding-block-start", "label": "Top padding", "min": 0, "max": 100, "step": 1, "unit": "px", "default": 16 },
    { "type": "range", "id": "padding-block-end", "label": "Bottom padding", "min": 0, "max": 100, "step": 1, "unit": "px", "default": 16 }
  ],
  "presets": [{ "name": "Product specs", "category": "Product" }]
}
{% endschema %}'''

with open(THEME_FILE, 'w') as f:
    f.write(liquid)

print(f"Generated {THEME_FILE}")
