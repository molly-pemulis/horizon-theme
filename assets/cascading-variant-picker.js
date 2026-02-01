/**
 * CASCADING VARIANT PICKER
 * ========================
 * Handles progressive variant selection:
 * 1. Only available variants shown
 * 2. Each dropdown enables after previous selection
 * 3. Filters options based on previous selections
 */

class CascadingVariantPicker extends HTMLElement {
  constructor() {
    super();
    this.variants = [];
    this.options = [];
    this.selections = [];
  }

  connectedCallback() {
    // Parse variant and option data from JSON scripts
    const variantsScript = this.querySelector('script[data-variants]');
    const optionsScript = this.querySelector('script[data-options]');
    
    if (variantsScript) {
      this.variants = JSON.parse(variantsScript.textContent);
    }
    if (optionsScript) {
      this.options = JSON.parse(optionsScript.textContent);
    }
    
    // Initialize selections array (one per option)
    this.selections = new Array(this.options.length).fill(null);
    
    // Bind change events to all selects
    this.querySelectorAll('select').forEach(select => {
      select.addEventListener('change', this.handleChange.bind(this));
    });
  }

  handleChange(event) {
    const select = event.target;
    const optionIndex = parseInt(select.dataset.optionIndex);
    const value = select.value;
    
    // Update selection
    this.selections[optionIndex] = value;
    
    // Clear all selections after this one
    for (let i = optionIndex + 1; i < this.selections.length; i++) {
      this.selections[i] = null;
    }
    
    // Update subsequent dropdowns
    this.updateDropdowns(optionIndex);
    
    // Check if we have a complete selection
    this.checkComplete();
  }

  updateDropdowns(fromIndex) {
    const selects = this.querySelectorAll('select');
    
    // Update each dropdown after the changed one
    for (let i = fromIndex + 1; i < selects.length; i++) {
      const select = selects[i];
      const availableValues = this.getAvailableValues(i);
      
      // Clear existing options (except placeholder)
      while (select.options.length > 1) {
        select.remove(1);
      }
      
      // Add available options
      availableValues.forEach(value => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      });
      
      // Enable/disable based on previous selection
      const previousSelected = this.selections[i - 1] !== null;
      select.disabled = !previousSelected;
      
      // Reset to placeholder
      select.selectedIndex = 0;
    }
  }

  getAvailableValues(optionIndex) {
    // Filter variants that match all previous selections
    let matchingVariants = this.variants;
    
    for (let i = 0; i < optionIndex; i++) {
      if (this.selections[i] !== null) {
        matchingVariants = matchingVariants.filter(v => v.options[i] === this.selections[i]);
      }
    }
    
    // Get unique values for this option from matching variants
    const values = [...new Set(matchingVariants.map(v => v.options[optionIndex]))];
    return values;
  }

  checkComplete() {
    const allSelected = this.selections.every((s, i) => s !== null || i >= this.options.length);
    const statusEl = this.querySelector('[data-status]');
    const hiddenInput = this.querySelector('[data-selected-variant-id]');
    
    if (this.selections.filter(s => s !== null).length === this.options.length) {
      // Find matching variant
      const variant = this.variants.find(v => 
        v.options.every((opt, i) => opt === this.selections[i])
      );
      
      if (variant) {
        hiddenInput.value = variant.id;
        statusEl.textContent = 'Ready to add to cart';
        statusEl.dataset.ready = 'true';
        
        // Dispatch event for other components (price, images, add to cart)
        this.dispatchEvent(new CustomEvent('variant:selected', {
          bubbles: true,
          detail: { variant }
        }));
      }
    } else {
      hiddenInput.value = '';
      statusEl.textContent = 'Select options above';
      statusEl.dataset.ready = 'false';
    }
  }
}

if (!customElements.get('cascading-variant-picker')) {
  customElements.define('cascading-variant-picker', CascadingVariantPicker);
}
