# Contract Placeholder Modification Guide

## Document Analysis

**Current Status**: The contract already has basic placeholders in place ✅

**Document**: 12. [Draft HA] Contract Productie, Management Artist [360] si impresariere - Copy
**Google Docs URL**: https://docs.google.com/document/d/1Pe2B7vnoH-KvYbW_IM7kyk3b4t1MNoZ3E8SQVNlFkwE/edit

---

## Modifications Needed

### 1. **Commission Sections (Lines 184-200)** - ADD CONDITIONAL SECTIONS & PHRASE PLACEHOLDERS

**Current text:**
```
Pentru Veniturile din Concerte :
			în primii 2 ani contractuali: Întâi, se vor deduce Cheltuielile, daca acestea nu au fost asigurate de către Organizatorul de Evenimente
Apoi, PRODUCATORUL va fi remunerat cu o sumă reprezentând un comision de {{commission.first_years.concert}} %;
...
			În [ultimul] 1 an/i contractual/i: Întâi, se vor deduce Cheltuielile, daca acestea nu au fost asigurate de către Organizatorul de Evenimente ;
Apoi, PRODUCĂTORUL va fi remunerat cu o sumă reprezentând un comision de {{commission.last_years.concert}}%;
```

**Replace with:**
```
Pentru Veniturile din Concerte :

{{BEGIN:concert_uniform}}
Pe toată durata contractului: Întâi, se vor deduce Cheltuielile, daca acestea nu au fost asigurate de către Organizatorul de Evenimente.
Apoi, PRODUCATORUL va fi remunerat cu o sumă reprezentând un comision de {{commission.concert.uniform}}%.
Din diferența dintre Venitul încasat si comisionul PRODUCĂTORULUI, suma rămasă se va achita ARTISTULUI, urmând ca acesta din urma sa achite toate costurile legate de trupa, backline, tour manager, echipa tehnica, sunet, lumini, video sau orice alte costuri cu personal conex/promovare/de producție – necesare desfășurării evenimentului.
{{END:concert_uniform}}

{{BEGIN:concert_first_years}}
{{concert_first_years.phrase:În primul {n} an contractual:În primii {n} ani contractuali}}: Întâi, se vor deduce Cheltuielile, daca acestea nu au fost asigurate de către Organizatorul de Evenimente.
Apoi, PRODUCATORUL va fi remunerat cu o sumă reprezentând un comision de {{commission.concert.first_years}}%.
Din diferența dintre Venitul încasat si comisionul PRODUCĂTORULUI, suma rămasă se va achita ARTISTULUI, urmând ca acesta din urma sa achite toate costurile legate de trupa, backline, tour manager, echipa tehnica, sunet, lumini, video sau orice alte costuri cu personal conex/promovare/de producție – necesare desfășurării evenimentului.

{{concert_last_years.phrase:În ultimul {n} an contractual:În ultimii {n} ani contractuali}}: Întâi, se vor deduce Cheltuielile, daca acestea nu au fost asigurate de către Organizatorul de Evenimente.
Apoi, PRODUCĂTORUL va fi remunerat cu o sumă reprezentând un comision de {{commission.concert.last_years}}%.
Din diferența dintre Venitul încasat si comisionul PRODUCĂTORULUI, suma rămasă se va achita ARTISTULUI, urmând ca acesta din urma sa achite toate costurile legate de trupa, backline, tour manager, echipa tehnica, sunet, lumini, video sau orice alte costuri cu personal conex/promovare/de producție – necesare desfășurării evenimentului.
{{END:concert_first_years}}
```

---

### 2. **Merchandising Section (Line 200+)** - ADD CONDITIONAL SECTION

The document shows "Pentru drepturi din merchandising ARTIST" but appears cut off.

**Add this structure:**
```
{{BEGIN:has_merchandising_rights}}
Pentru drepturi din merchandising ARTIST:

{{BEGIN:merchandising_uniform}}
Pe toată durata contractului, PRODUCĂTORUL va primi {{commission.merchandising.uniform}}% din veniturile nete generate din vânzarea de produse de merchandising.
{{END:merchandising_uniform}}

{{BEGIN:merchandising_first_years}}
{{merchandising_first_years.phrase:În primul {n} an contractual:În primii {n} ani contractuali}}, PRODUCĂTORUL va primi {{commission.merchandising.first_years}}% din veniturile nete generate din vânzarea de produse de merchandising.

{{merchandising_last_years.phrase:În ultimul {n} an contractual:În ultimii {n} ani contractuali}}, PRODUCĂTORUL va primi {{commission.merchandising.last_years}}% din veniturile nete generate din vânzarea de produse de merchandising.
{{END:merchandising_first_years}}
{{END:has_merchandising_rights}}
```

---

### 3. **Image Rights Section** - ADD IF MISSING

Add this section for image rights commission:

```
{{BEGIN:has_image_rights_rights}}
Pentru Drepturile de Imagine ale Artistului:

{{BEGIN:image_rights_uniform}}
Pe toată durata contractului, din veniturile încasate din exploatarea drepturilor de imagine ale ARTISTULUI, PRODUCĂTORUL va primi un comision de {{commission.image_rights.uniform}}%.
{{END:image_rights_uniform}}

{{BEGIN:image_rights_first_years}}
{{image_rights_first_years.phrase:În primul {n} an contractual:În primii {n} ani contractuali}}, din veniturile încasate din exploatarea drepturilor de imagine ale ARTISTULUI, PRODUCĂTORUL va primi un comision de {{commission.image_rights.first_years}}%.

{{image_rights_last_years.phrase:În ultimul {n} an contractual:În ultimii {n} ani contractuali}}, din veniturile încasate din exploatarea drepturilor de imagine ale ARTISTULUI, PRODUCĂTORUL va primi un comision de {{commission.image_rights.last_years}}%.
{{END:image_rights_first_years}}
{{END:has_image_rights_rights}}
```

---

### 4. **Rights (Recording Rights) Section** - ADD IF MISSING

```
{{BEGIN:has_rights_rights}}
Pentru Drepturile de Înregistrare (Rights):

{{BEGIN:rights_uniform}}
Pe toată durata contractului, PRODUCĂTORUL va primi {{commission.rights.uniform}}% din veniturile nete generate din exploatarea drepturilor de înregistrare.
{{END:rights_uniform}}

{{BEGIN:rights_first_years}}
{{rights_first_years.phrase:În primul {n} an contractual:În primii {n} ani contractuali}}, PRODUCĂTORUL va primi {{commission.rights.first_years}}% din veniturile nete generate din exploatarea drepturilor de înregistrare.

{{rights_last_years.phrase:În ultimul {n} an contractual:În ultimii {n} ani contractuali}}, PRODUCĂTORUL va primi {{commission.rights.last_years}}% din veniturile nete generate din exploatarea drepturilor de înregistrare.
{{END:rights_first_years}}
{{END:has_rights_rights}}
```

---

### 5. **Update PPD, EMD, Sync Sections (Lines 194-197)**

**Current:**
```
{{commission.first_years.ppd}}% din PPD-ul PRODUCĂTORULUI...
{{commission.first_years.emd}}% din venitul net încasat...
{{commission.first_years.sync}}% din venitul net încasat...
```

**Replace with:**
```
{{BEGIN:has_ppd_rights}}
{{BEGIN:ppd_uniform}}
{{commission.ppd.uniform}}% din PPD-ul PRODUCĂTORULUI pentru fiecare Unitate fizica, incasata si nereturnata.
{{END:ppd_uniform}}
{{BEGIN:ppd_first_years}}
{{ppd_first_years.phrase:În primul {n} an contractual:În primii {n} ani contractuali}}: {{commission.ppd.first_years}}% din PPD-ul PRODUCĂTORULUI.
{{ppd_last_years.phrase:În ultimul {n} an contractual:În ultimii {n} ani contractuali}}: {{commission.ppd.last_years}}% din PPD-ul PRODUCĂTORULUI.
{{END:ppd_first_years}}
{{END:has_ppd_rights}}

{{BEGIN:has_emd_rights}}
{{BEGIN:emd_uniform}}
În cazul veniturilor obținute din EMD: {{commission.emd.uniform}}% din venitul net încasat de PRODUCATOR de la terți.
{{END:emd_uniform}}
{{BEGIN:emd_first_years}}
{{emd_first_years.phrase:În primul {n} an contractual:În primii {n} ani contractuali}}: {{commission.emd.first_years}}% din venitul net EMD încasat.
{{emd_last_years.phrase:În ultimul {n} an contractual:În ultimii {n} ani contractuali}}: {{commission.emd.last_years}}% din venitul net EMD încasat.
{{END:emd_first_years}}
{{END:has_emd_rights}}

{{BEGIN:has_sync_rights}}
{{BEGIN:sync_uniform}}
Pentru sincronizare și publicitate: {{commission.sync.uniform}}% din venitul net încasat de PRODUCATOR.
{{END:sync_uniform}}
{{BEGIN:sync_first_years}}
{{sync_first_years.phrase:În primul {n} an contractual:În primii {n} ani contractuali}}: {{commission.sync.first_years}}% din venitul net din sincronizare.
{{sync_last_years.phrase:În ultimul {n} an contractual:În ultimii {n} ani contractuali}}: {{commission.sync.last_years}}% din venitul net din sincronizare.
{{END:sync_first_years}}
{{END:has_sync_rights}}
```

---

### 6. **Contract Terms (Lines 82-84)** - UPDATE PLACEHOLDERS

**Current:**
```
Prezentul Contract este valabil pe o perioada de {{contract.duration_years}} (patru) ani...
...cu cel puțin {{contract.notice_period_days}} de zile înainte...
```

**Replace with:**
```
Prezentul Contract este valabil pe o perioada de {{contract_duration_years}} ani, începând cu data semnării si se poate prelungi prin act adițional semnat de părți.
Contractul se va prelungi in mod automat pentru noi perioade de 1 an in absenta unei notificări emise de partea care nu dorește prelungirea, cu cel puțin {{notice_period_days}} de zile înainte de expirare.
```

**Note**: Change `{{contract.*}}` to match what frontend sends: `{{contract_duration_years}}`, `{{notice_period_days}}`

---

### 7. **Investment Terms (Line 140)**

**Current:**
```
sa garanteze un număr minimum de {{contract.minimum_launches}} lansări pe an cu o valoare maxima de investiție de {{investment.per_song}} EUR pe piesa/pe an;
```

**Replace with:**
```
sa garanteze un număr minimum de {{minimum_launches_per_year}} lansări pe an cu o valoare maxima de investiție de {{max_investment_per_song}} EUR pe piesa/pe an, cu un plafon anual de {{max_investment_per_year}} EUR;
```

---

## Summary of Changes

### What's Already Good ✅
- Entity placeholders (name, address, city, etc.)
- Company placeholders (maincompany.*)
- Gender placeholders (entity.gender:masculine:feminine)
- Identification placeholders (entity.identification_full)
- Basic commission placeholders

### What Needs to Be Added ⚠️
1. **Conditional sections** (`{{BEGIN:...}}` / `{{END:...}}`) for uniform vs split commissions
2. **Phrase placeholders** (`{{variable.phrase:singular:plural}}`) for grammatically correct Romanian
3. **Has-rights sections** (`{{BEGIN:has_*_rights}}`) to hide entire categories when disabled
4. **Nested conditional sections** for uniform inside split mode
5. **Standardized placeholder names** to match frontend payload

---

## How Backend Will Process This

When frontend sends:
```json
{
  "commission_by_year": {
    "1": {"concert": "20", "image_rights": "30"},
    "2": {"concert": "20", "image_rights": "30"},
    "3": {"concert": "10", "image_rights": "20"}
  },
  "enabled_rights": {
    "concert": true,
    "image_rights": true,
    "merchandising": false
  }
}
```

Backend generates:
```
concert_uniform = 0 (split mode)
concert_first_years = 2
concert_last_years = 1
commission.concert.first_years = 20
commission.concert.last_years = 10
has_merchandising_rights = 0 (hidden)
```

Result in contract:
- `{{BEGIN:concert_uniform}}` section → HIDDEN
- `{{BEGIN:concert_first_years}}` section → SHOWN with "În primii 2 ani" and "În ultimul 1 an"
- `{{BEGIN:has_merchandising_rights}}` → ENTIRE merchandising section HIDDEN

---

## Next Steps

1. **Open the Google Doc** manually (storage quota exceeded for copying)
2. **Apply modifications** from sections 1-7 above
3. **Test with real entity data** from the system
4. **Register as template** in the backend

---

## Testing Recommendations

Test with these scenarios:

**Scenario 1: All Uniform Rates**
- All years same percentage
- Expected: Only uniform sections shown

**Scenario 2: Split Rates (Years 1-2 vs Year 3)**
- First 2 years at 25%, last year at 15%
- Expected: "În primii 2 ani" and "În ultimul 1 an" shown

**Scenario 3: Disabled Rights**
- Merchandising disabled
- Expected: Entire merchandising section hidden

**Scenario 4: Single Year Contract**
- Duration = 1 year
- Expected: Singular forms ("În primul 1 an")

---

**Date**: 2025-10-30
**Author**: Claude Code
**Status**: Ready for Manual Implementation (Google Drive quota exceeded - cannot auto-modify)
