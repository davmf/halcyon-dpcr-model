// Validate SysML v2 files with the OMG Pilot Implementation.
//
// Usage: java -cp <pilot-jar> PilotCheck.java <library-dir> <file.sysml>...
//
// Loads the standard library, reads all input files into one resource set
// (so cross-file references resolve), validates each input file and prints
// one line per issue:
//
//   ISSUE<TAB>SEVERITY<TAB>path<TAB>line<TAB>column<TAB>message
//
// Exit status: 0 when no ERROR, 1 otherwise, 2 on usage error.

import java.io.File;
import java.util.List;

import org.eclipse.emf.ecore.resource.Resource;
import org.eclipse.emf.ecore.util.EcoreUtil;
import org.eclipse.xtext.resource.XtextResource;
import org.eclipse.xtext.util.CancelIndicator;
import org.eclipse.xtext.validation.CheckMode;
import org.eclipse.xtext.validation.Issue;
import org.omg.sysml.interactive.SysMLInteractive;

public class PilotCheck {
    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("usage: PilotCheck <library-dir> <file>...");
            System.exit(2);
        }
        String library = args[0].endsWith("/") ? args[0] : args[0] + "/";
        SysMLInteractive pilot = SysMLInteractive.getInstance();
        pilot.setVerbose(false);
        pilot.loadLibrary(library);

        for (int i = 1; i < args.length; i++) {
            String path = new File(args[i]).getAbsolutePath();
            Resource resource = pilot.readResource(path);
            if (resource == null) {
                System.out.println(
                    "ISSUE\tERROR\t" + args[i] + "\t0\t0\tCannot read file");
                continue;
            }
            pilot.addInputResource(resource);
        }
        for (Resource resource : pilot.getInputResources()) {
            EcoreUtil.resolveAll(resource);
        }

        int errors = 0;
        for (Resource resource : pilot.getInputResources()) {
            String path = resource.getURI().toFileString();
            List<Issue> issues = ((XtextResource) resource)
                .getResourceServiceProvider()
                .getResourceValidator()
                .validate(resource, CheckMode.ALL, CancelIndicator.NullImpl);
            for (Issue issue : issues) {
                if (issue.getSeverity() == org.eclipse.xtext.diagnostics.Severity.ERROR) {
                    errors++;
                }
                String message = issue.getMessage() == null
                    ? "" : issue.getMessage().replace('\n', ' ').replace('\t', ' ');
                System.out.println(
                    "ISSUE\t" + issue.getSeverity() + "\t" + path + "\t"
                    + issue.getLineNumber() + "\t" + issue.getColumn() + "\t"
                    + message);
            }
        }
        System.out.println("SUMMARY\t" + pilot.getInputResources().size()
            + " files\t" + errors + " errors");
        System.exit(errors == 0 ? 0 : 1);
    }
}
