package StrictDocWorkspace {
    doc /*
     * Metadata of the StrictDoc tracker layout. A model root lists its
     * trackers, a tracker or a folder lists its folders and items, each
     * with `public import '<ID>'::*;`. Every top-level package name is an ID.
     */

    private import ScalarValues::*;

    metadata def Model {
        attribute title : String;
    }

    metadata def Tracker {
        doc /* kind: requirements, test cases, design, behaviour... */
        attribute title : String;
        attribute kind : String;
        attribute prefix : String;
    }

    metadata def Folder {
        attribute title : String;
    }

    metadata def DiagramView {
        doc /*
         * On a view item: the !include_sysml options of the diagram and
         * PlantUML lines added after the directive (notes, styles).
         */
        attribute options : String;
        attribute plantuml : String;
    }
}
