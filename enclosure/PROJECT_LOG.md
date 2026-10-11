# Enclosure project log — 2026-10-11

User requested a polished, FlowSight-branded printable enclosure to house the existing external ESP32 display and sell assembled devices. Existing project reused at E:\codex_sessions\flowsight-esp32\enclosure. E: available with about 1.3 TB free at start.

Hardware responses: first ESP32-2432S028R 2.8 inches, subsequently same CS-32 N4XX already connected. The firmware documentation confirms 024-compatible wiring but does not establish mechanical identity. Asked for millimetre measurements; user answered "si" without dimensions. Completed one common design with distinct 024-reference and 028 front/fit-check configurations; explicit physical fit limitation retained. No board photographs of the user's actual unit were available.

Dimensional correction: original diagrams label mounting pitches, not board exterior dimensions. 028 pitch is 78 x 42 mm, original body about 86 x 50 mm. 024 pitch is 68 x 36.5 mm, body 74.4 x 42.9 mm. The initial shorthand in commentary was corrected before CAD generation.

Sources:
- https://github.com/witnessmenow/ESP32-Cheap-Yellow-Display/blob/main/OriginalDocumentation/3-Structure_Diagram/Dimensions.png
- https://github.com/witnessmenow/ESP32-Cheap-Yellow-Display/blob/main/3dModels/Havenview_CYD_CAD/Cheap%20Yellow%20Display%20v16.step — board solid measured 86.6 x 50 x 9.8 mm; unrelated case/stand solids not used.
- https://www.inventech.co.za/shop/development-boards-1/cheap-yellow-display-esp32-50 — module 86 x 50 mm.
- https://github.com/jpduhen/CYD_2.4inch_ESP32-2432S024/blob/main/3-Structure_Diagram/Dimensions.png
- https://github.com/jpduhen/CYD_2.4inch_ESP32-2432S024/blob/main/2-Specification/ESP32-2432S024%20Specifications-EN.pdf — body 74.4 x 42.9 mm, active 48.96 x 36.72 mm.

Design: original CadQuery BREP construction, rounded 104 x 78 mm front housing, 2.4 mm walls, 0.6 mm engraving from official FlowSight alpha-mask logo and Manrope Bold wordmark. Housing screws at rear; independent four-post PCB support; universal rear service hatch; lateral open cable alcove; 65-degree desk cradle with rubber-foot pockets. Optional 0.4/0.8/1.2 mm board spacers and two low-material fit templates.

All exported printable meshes checked for watertightness, consistent winding, positive volume, CAD solid validity. Major parts each one connected closed solid. Brand insert is intentionally 14 connected glyph/logo solids, each closed. Standard 3MF layout written with mm units, named components and positions over a 214 x 148 mm footprint. No printer-specific G-code issued.

Both configurations checked for zero CAD intersection volume between PCB envelope and housing, housing/lid, lid/hatch, stand/housing. These digital checks do not cover unknown CS-32 component locations, exact connector revision, printer tolerances, touch pressure, physical stability or heat performance. First printed fit/unit remains required before commercial batch production.

Preview strategy: Blender renders directly import the exported printable meshes and place them in assembly coordinates. Screen is the project's existing firmware-rendered Spanish test snapshot; LCD/PCB/hardware depicted as illustrative nonprinted components. Images are explicitly labelled renders in delivery. Inspection outcomes and final file manifest appended after generation.
