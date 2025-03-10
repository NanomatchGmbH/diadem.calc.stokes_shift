# Contents

The content of this folder is generated from the diadem userscripts listing PCT
It is assumed, you added new calculators using "add_calculator.sh" (step 1.)
Now, you want to add `id` to the calculator specifications.

# How to generate files.

## 1. Generate the `list_pct.txt`.
```commandline
bash ./list_pct.sh >> ~/Desktop/test_diadem.calc.mobiity/diadem.calc.mobility/calculators/to_diadem/120_2.0.2/txt/list_pct.txt
```

## 2. Generate the `list_calculators.txt`
```commandline
bash list_calculators.sh >> ~/Desktop/test_diadem.calc.mobiity/diadem.calc.mobility/calculators/to_diadem/120_2.0.2/txt/list_calculators.txt
```

## 3. Clean up.

Remove everything from `.txt` files before `1.`