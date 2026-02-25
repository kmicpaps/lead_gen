# Email Copy

---

## Email Info

| Field | Value |
|-------|-------|
| **ID** | `unique_id_here` |
| **Position** | `initial` / `followup_1` /  `followup_2` / 
| **Style** | `curiosity` / `direct` / `value_first` / `social_proof` / `pattern_interrupt` / `short_bump` / `question` / `light_humor` |
| **Tone** | `casual` / `professional` / `helpful` / `direct` |
| **Delay Days** | `0` for initial, `2`, / `2` / for follow-ups |

---

icebreaker tempalte: Uzgāju Jūsu LinkedIn kontu un papētīju, ar ko nodarbojaties iekš {Casual comapny name} uzņēmuma. Tā ir tāda ļoti pateicīga industrija pakalpojumam, ko piedāvāju, un, par cik Jūs esat {title}, tad domāju, ka esat īstais cilvēks, ko uzrunāt.

## Subject Line 

```
{{first_name_inflection}}, šis jau vairs nav smieklīgi!

---

## Body A

```
Labi, piedod, {{first_name_inflection}}, viss ir kārtībā, bet kaut kā vajadzēja pievērst Jūsu uzmanību. :)

{{icebreaker}}

Piedāvājums ir pavisam vienkāršs - mēs Jums izveidotu efektīvu e-pastu mārketinga robotu, kas, izmantojot mākslīgo intelektu, sūtīs personalizētus un ļoti efektīvus pārdošanas e-pastus ideālajai mērķauditorijai (jā, piedod, arī šis e-pasts ir uzrakstīts tieši tādā veidā... bet, ja Jūs esat tik tālu izlasījuši, tas nozīmē tikai vienu - tas strādā:) ). 

Labās ziņas Jums - Latvijā to izmanto tikai pāris uzņēmumi, kas nozīmē, ka Jūs šo esat pamanījuši diezgan agri, un, kā jau visur dzīvē - kas pirmais brauc, tas pirmais maļ. Pagaidām rezultāti ir neticami labi, un es ļoti vēlētos, lai arī Jūs sāktu strādāt ar mums, un mums būtu vēlviens veiksmes stāsts ar ko padalīties.

Lūdzu, dodiet ziņu, vai šis Jums būs aktuāli. Ja nav - lūdzu, atbildiet ar "Nē, paldies", un es Jūs izņemšu no saraksta, lai Jūs nesaņemtu ziņas.

Izdevušos dienu vēlot,
{{sender_name}} no {{sender_company}}
```
## Body B
Labi, piedod, {{first_name_inflection}}, viss ir kārtībā, bet kaut kā vajadzēja pievērst Jūsu uzmanību. :)

{{icebreaker}}

Mani sauc {{sender_name}}, {{company_type}} Pamanu - labs piedāvājums, labas atsauksmes, bet izdzīvo uz klientu "referrals" un nav vienkārša veida, kā piemeklēt svaigus klientus.

Palīdzam izveidot Jūsu pirmo auksto epastu kampaņu. Tēmējam uz 5-10 pieteikumiem 30 dienu laikā pēc kampaņas izveides. Ja nesasniedzm mērķi - atgriržam investīcīju.

Mūsu klientiam visvairāk uzrunā, ka pielietojam jaunākās tehnoloģijas un AI. (jā, piedod, arī šis e-pasts ir uzrakstīts tieši tādā veidā... bet, ja Jūs esat tik tālu izlasījuši, tas nozīmē tikai vienu - tas strādā:). 

Latvijā to izmanto tikai pāris uzņēmumi, kas nozīmē, ka Jūs šo esat mūs atradis diezgan agri, un, kā jau visur dzīvē - kas pirmais brauc, tas pirmais maļ.

Lūdzu, dodiet ziņu, vai šis Jums būs aktuāli atbildot "Jā, interesē!". Ja nav - lūdzu, atbildiet ar "Nē, paldies", un es Jūs izņemšu no saraksta, lai Jūs nesaņemtu ziņas.

Izdevušos dienu vēlot,
{{sender_name}} no {{sender_company}}

- {{sender_name}}


## Follow up 1

Subject: {{first_name_inflection}}, vai patiešām...?
---

Body:
Sveiki, vēlreiz,

Redzēju, ka pirms 2 dienām atvērāt manu e-pastu, taču nedevāt nekādu atbildi. :(

Esam pierādījuši, ka daudz personalizētu e-pastu = daudz jaunu klientu, vai tiešām jaunu klientu piesaiste Jums vairs nav aktuāla?
Jums nebūs jāriskē ne ar ko - mēs piedāvājam pilnu servisu (darbinieks nebūs vajadzīgs), kā arī naudas atgriešanas garantiju, ja serviss Jums nepatiks.

Lūdzu, dodiet ziņu... esmu gatavs Jums palīdzēt un sniegt visērtāko servisu!

Daudz jaunu klientu vēlot,
{{sender_name}}

 
## Notes
- A good example on latvian inflections. for latvian it is important that the first name infections are accurate
- B2b in latvian

---

## Placeholders Reference

| Placeholder | Description |
|-------------|-------------|
| `{{first_name}}` | Lead's first name |
| `{{last_name}}` | Lead's last name |
| `{{company}}` | Company name |
| `{{title}}` | Job title |
| `{{industry}}` | Industry |
| `{{icebreaker}}` | Personalized intro from enrichment |
| `{{sender_name}}` | Your name |
| `{{sender_company}}` | Your company name |

Example: {{first_name}}, your best client deserves a better lead magnet

Subject: {{first_name_inflection}}, šis jau vairs nav smieklīgi!

Body:

Labi, piedod, {{first_name_inflection}}, viss ir kārtībā, bet kaut kā vajadzēja pievērst Jūsu uzmanību. :)

Uzgāju Jūsu LinkedIn kontu un papētīju, ar ko nodarbojaties iekš {{company}}. Tā ir tāda ļoti pateicīga industrija pakalpojumam, ko piedāvāju, un, par cik Jūs esat uzņēmuma vadītājs un partneris, tad domāju, ka esat īstais cilvēks, ko uzrunāt.

Piedāvājums ir pavisam vienkāršs - mēs Jums izveidotu efektīvu e-pastu mārketinga robotu, kas, izmantojot mākslīgo intelektu, sūtīs personalizētus un ļoti efektīvus pārdošanas e-pastus ideālajai mērķauditorijai (jā, piedod, arī šis e-pasts ir uzrakstīts tieši tādā veidā... bet, ja Jūs esat tik tālu izlasījuši, tas nozīmē tikai vienu - tas strādā:) ).

Labās ziņas Jums - Latvijā to izmanto tikai pāris uzņēmumi, kas nozīmē, ka Jūs šo esat pamanījuši diezgan agri, un, kā jau visur dzīvē - kas pirmais brauc, tas pirmais maļ. Pagaidām rezultāti ir neticami labi, un es ļoti vēlētos, lai arī Jūs sāktu strādāt ar mums, un mums būtu vēlviens veiksmes stāsts ar ko padalīties.

Lūdzu, dodiet ziņu, vai šis Jums būs aktuāli. Ja nav - lūdzu, atbildiet ar "Nē, paldies", un es Jūs izņemšu no saraksta, lai Jūs nesaņemtu ziņas.

Izdevušos dienu vēlot,
{{sender_name}} no {{sender_company}}