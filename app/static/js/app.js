/**
 * PocketSmart AI - Client-side Interactive Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Current Year in Footer
  const yearElem = document.getElementById('currentYear');
  if (yearElem) {
    yearElem.textContent = new Date().getFullYear();
  }

  // 2. Mobile Navigation Toggle
  const navToggle = document.getElementById('navToggle');
  const mainNav = document.getElementById('mainNav');
  if (navToggle && mainNav) {
    navToggle.addEventListener('click', () => {
      mainNav.classList.toggle('active');
    });
  }

  // Currency Formatter Utility
  const formatINR = (amount) => {
    return '₹' + Number(amount).toLocaleString('en-IN');
  };

  // Toast Notification Helper
  const showToast = (message) => {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span>✨</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.4s ease';
      setTimeout(() => toast.remove(), 400);
    }, 3000);
  };

  // 3. Home Planner: Slider & Number Input Sync
  const budgetSlider = document.getElementById('budgetSlider');
  const budgetInput = document.getElementById('budget');
  const homeBudgetDisplay = document.getElementById('homeBudgetDisplay');

  if (budgetSlider && budgetInput && homeBudgetDisplay) {
    const updateHomeBudget = (val) => {
      budgetSlider.value = val;
      budgetInput.value = val;
      homeBudgetDisplay.textContent = formatINR(val);
    };

    budgetSlider.addEventListener('input', (e) => updateHomeBudget(e.target.value));
    budgetInput.addEventListener('input', (e) => updateHomeBudget(e.target.value || 0));
  }

  // 4. Party Planner: Budget & Guest Count Sync with Live Per-Head Cost
  const partySlider = document.getElementById('partyBudgetSlider');
  const partyInput = document.getElementById('partyBudget');
  const partyDisplay = document.getElementById('partyBudgetDisplay');
  const guestCountInput = document.getElementById('guest_count');
  const perHeadBadge = document.getElementById('perHeadBadge');

  if (partySlider && partyInput && partyDisplay && guestCountInput && perHeadBadge) {
    const updatePartyCalculations = () => {
      const budget = parseFloat(partyInput.value) || 0;
      const guests = Math.max(1, parseInt(guestCountInput.value) || 1);
      const perHead = Math.round(budget / guests);

      partySlider.value = budget;
      partyDisplay.textContent = formatINR(budget);
      perHeadBadge.textContent = `${formatINR(perHead)} / guest`;
    };

    partySlider.addEventListener('input', (e) => {
      partyInput.value = e.target.value;
      updatePartyCalculations();
    });
    partyInput.addEventListener('input', updatePartyCalculations);
    guestCountInput.addEventListener('input', updatePartyCalculations);
  }

  // 5. Jewelry Planner: Budget Slider & Number Input Sync
  const jewelrySlider = document.getElementById('jewelryBudgetSlider');
  const jewelryInput = document.getElementById('jewelryBudget');
  const jewelryDisplay = document.getElementById('jewelryBudgetDisplay');

  if (jewelrySlider && jewelryInput && jewelryDisplay) {
    const updateJewelryBudget = (val) => {
      jewelrySlider.value = val;
      jewelryInput.value = val;
      jewelryDisplay.textContent = formatINR(val);
    };

    jewelrySlider.addEventListener('input', (e) => updateJewelryBudget(e.target.value));
    jewelryInput.addEventListener('input', (e) => updateJewelryBudget(e.target.value || 0));
  }

  // 6. Jewelry Planner: Multimodal Outfit Image Drag-and-Drop & Preview
  const imageInput = document.getElementById('outfitImageInput');
  const dropzone = document.getElementById('uploadDropzone');
  const dropzonePrompt = document.getElementById('dropzonePrompt');
  const previewWrap = document.getElementById('imagePreviewWrap');
  const imagePreview = document.getElementById('imagePreview');
  const removeImageBtn = document.getElementById('removeImageBtn');

  if (imageInput && dropzone && previewWrap && imagePreview) {
    const handleFile = (file) => {
      if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          imagePreview.src = e.target.result;
          dropzonePrompt.style.display = 'none';
          previewWrap.style.display = 'inline-block';
        };
        reader.readAsDataURL(file);
      }
    };

    imageInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        handleFile(e.target.files[0]);
      }
    });

    if (removeImageBtn) {
      removeImageBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        imageInput.value = '';
        imagePreview.src = '';
        previewWrap.style.display = 'none';
        dropzonePrompt.style.display = 'block';
      });
    }

    // Drag-over styling
    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.style.borderColor = 'var(--primary)';
      dropzone.style.backgroundColor = 'var(--primary-light)';
    });

    dropzone.addEventListener('dragleave', () => {
      dropzone.style.borderColor = '#cbd5e1';
      dropzone.style.backgroundColor = '#f8fafc';
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.style.borderColor = '#cbd5e1';
      dropzone.style.backgroundColor = '#f8fafc';
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        imageInput.files = e.dataTransfer.files;
        handleFile(e.dataTransfer.files[0]);
      }
    });
  }

  // 7. Form Submit Loading Spinners
  const setupFormLoading = (formId, btnId, loadingId) => {
    const form = document.getElementById(formId);
    const btn = document.getElementById(btnId);
    const loading = document.getElementById(loadingId);

    if (form && btn && loading) {
      form.addEventListener('submit', () => {
        btn.style.display = 'none';
        loading.style.display = 'block';
      });
    }
  };

  setupFormLoading('homePlannerForm', 'submitBtn', 'formLoading');
  setupFormLoading('partyPlannerForm', 'partySubmitBtn', 'partyFormLoading');
  setupFormLoading('jewelryPlannerForm', 'jewelrySubmitBtn', 'jewelryFormLoading');

  // 8. Copy Plan Summary Button on Recommendations Page
  const copyPlanBtn = document.getElementById('copyPlanBtn');
  if (copyPlanBtn) {
    copyPlanBtn.addEventListener('click', () => {
      const titleElem = document.querySelector('.results-title');
      const noteElem = document.querySelector('.budget-note-text');
      const productCards = document.querySelectorAll('.product-card');

      let planText = `PocketSmart AI Plan Summary\n===========================\n`;
      if (titleElem) planText += `Summary: ${titleElem.textContent.trim()}\n`;
      if (noteElem) planText += `Strategy: ${noteElem.textContent.trim()}\n\n`;

      planText += `Curated Recommendations:\n------------------------\n`;
      productCards.forEach((card, idx) => {
        const name = card.querySelector('.product-name')?.textContent.trim();
        const price = card.querySelector('.price-amount')?.textContent.trim();
        const platform = card.querySelector('.platform-badge')?.textContent.trim();
        const reason = card.querySelector('.product-reason')?.textContent.trim();
        planText += `${idx + 1}. [${platform}] ${name} - ${price}\n   Why: ${reason}\n\n`;
      });

      planText += `Generated via PocketSmart AI (https://pocketsmart.ai)`;

      navigator.clipboard.writeText(planText).then(() => {
        showToast('Plan summary copied to clipboard!');
      }).catch(() => {
        showToast('Copied to clipboard!');
      });
    });
  }

  // 9. Quick Demo Login Credentials Autofill
  const btnFillDemo = document.getElementById('btnFillDemo');
  if (btnFillDemo) {
    btnFillDemo.addEventListener('click', () => {
      const usernameInput = document.getElementById('username');
      const passwordInput = document.getElementById('password');
      if (usernameInput && passwordInput) {
        usernameInput.value = 'demo_user';
        passwordInput.value = 'demo1234';
        showToast('Demo credentials filled!');
      }
    });
  }
});
